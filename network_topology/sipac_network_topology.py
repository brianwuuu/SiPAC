import itertools, pprint
from network_topology.network_topology import *

class SiPACNetworkTopology(NetworkTopology):
    def __init__(self, r, l, link_bw, num_wavelengths_per_pair=1):
        NetworkTopology.__init__(self)
        self.name = "sipac"
        self.switch_radix = r
        self.num_levels = l + 1
        self.num_groups = r ** l # number of base groups
        assert(l >= 1)
        # Switches
        self.num_switches_in_level = [r ** level for level in range(self.num_levels)]
        # Computing Nodes
        self.num_gpus_per_group = r # number of switches per group
        self.num_gpus = r ** (l+1) # total number of gpus in the topology
        self.gpus = [list(range(i*self.num_gpus_per_group, (i+1)*self.num_gpus_per_group)) for i in range(self.num_groups)]
        self.total_num_optical_switches = r ** l * (l + 1) # not counting the nvswitches. Originally: (r ** l * (l + 1))
        self.adjacency_matrix = [[0]*(self.num_gpus) for _ in range(self.num_gpus)]
        self.total_num_links = self.total_num_optical_switches * self.switch_radix # physically not logically
        # Links
        self.num_wavelengths_per_pair = num_wavelengths_per_pair
        self.link_bw = link_bw

    def getName(self):
        network_name = self.name + "_{}r_{}l".format(self.num_gpus_per_group, self.num_levels-1)
        return network_name
    
    def getTopologyName(self):
        return "SiPAC"
    
    def getNumServers(self):
        return self.num_gpus

    def getNumSwitches(self):
        return self.total_num_optical_switches
    
    def getNumLinks(self):
        return self.total_num_links
    
    def getNumTransceivers(self):
        assert(self.num_gpus * self.num_levels == self.total_num_links)
        return self.num_gpus * self.num_levels

    def getR(self):
        return self.num_gpus_per_group
    
    def getL(self):
        return self.num_levels - 1
    
    def getNumGPUsPerGroup(self):
        return self.num_gpus_per_group
    
    def getLinkBW(self):
        return self.link_bw
    
    def getAdjacencyMatrix(self):
        return self.adjacency_matrix
    
    def designIntraGroupTopology(self):
        # V1: exactly like a level-0 bcube
        # All GPUs connect to a non-blocking OCS which is effectively an all-to-all fullmesh
        self.gpu_groups = []
        for i in range(self.num_groups):
            self.gpu_groups.append(list(range(i*self.num_gpus_per_group, (i+1)*self.num_gpus_per_group)))
            for j in range(i*self.num_gpus_per_group, (i+1)*self.num_gpus_per_group):
                for k in range(j, (i+1)*self.num_gpus_per_group):
                    if j != k:
                        self.adjacency_matrix[j][k] = self.num_wavelengths_per_pair
                        self.adjacency_matrix[k][j] = self.num_wavelengths_per_pair
        return

    def designInterGroupTopology(self, level):
        # For a canonical design, for each level, connect all gpus in an alltoall fullmesh
        num_iteration = self.num_groups // self.num_switches_in_level[level]
        num_groups_per_iteration = len(self.gpu_groups) // num_iteration
        for i in range(num_iteration):
            group_list = [group for group in self.gpu_groups[i*num_groups_per_iteration:(i+1)*num_groups_per_iteration]]
            self.connectSameIndexNodes(group_list)
            # merge groups that have just been connected
        self.gpu_groups = [list(itertools.chain.from_iterable(self.gpu_groups[i*num_groups_per_iteration:(i+1)*num_groups_per_iteration])) for i in range(num_iteration)]
        return

    def connectSameIndexNodes(self, group_list):
        # group_list is a list of lists with same length
        # this function connects the nodes of the same index in each of the lists in a full mesh
        num_gpus_per_group = len(group_list[0])
        for gpu_id in range(num_gpus_per_group):
            for src_group_id in range(len(group_list)):
                src_gpu = group_list[src_group_id][gpu_id]
                for dst_group_id in range(src_group_id+1, len(group_list)):
                    dst_gpu = group_list[dst_group_id][gpu_id]
                    assert(src_group_id != dst_group_id and src_gpu != dst_gpu)
                    self.adjacency_matrix[src_gpu][dst_gpu] = self.num_wavelengths_per_pair
                    self.adjacency_matrix[dst_gpu][src_gpu] = self.num_wavelengths_per_pair
    
    def wireNetwork(self):
        print("[Setup] Wiring SiPAC network.")
        self.designIntraGroupTopology()
        for level in range(1, self.num_levels):
            self.designInterGroupTopology(level)
        # All servers (GPUs) overlap with ToRs
        for src in range(len(self.adjacency_matrix)):
            self.adjacency_list[src] = {}
            # add destination switches
            for dst in range(len(self.adjacency_matrix[src])):
                if self.adjacency_matrix[src][dst] != 0:
                    self.adjacency_list[src][dst] = self.adjacency_matrix[src][dst]
    
    # Generates the topology string used for netbench.
    def generateTopologyFileString(self):
        prefix = ""
        topol_str = ""
        num_edges = 0
        for switch_id in self.adjacency_list:
            for target_switch_id in self.adjacency_list[switch_id]:
                link_count = int(self.adjacency_list[switch_id][target_switch_id])
                num_edges += link_count
                for _ in range(link_count):
                    topol_str += "{} {}\n".format(switch_id, target_switch_id)
        num_switches = len(self.adjacency_list)
        prefix += ("|V|={}".format(num_switches) + "\n")
        prefix += ("|E|={}".format(num_edges) + "\n")
        prefix += "ToRs=incl_range({},{})\n".format(self.gpus[0][0], self.gpus[-1][-1])
        prefix += "Servers=incl_range({},{})\n".format(self.gpus[0][0], self.gpus[-1][-1])
        prefix += ("Switches=set()\n\n")
        return prefix + topol_str
    
    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        number_of_flows = 0
        gpu_offset = 0
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            src, dst = src + gpu_offset, dst + gpu_offset
            assert(src in self.adjacency_list and dst in self.adjacency_list)
            if src != dst:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src), int(dst), sum_bytes)
                number_of_flows += 1
        return str_builder, number_of_flows