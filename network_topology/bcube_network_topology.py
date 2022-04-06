import itertools
from network_topology.network_topology import *

class BcubeNetworkTopology(NetworkTopology):
    def __init__(self, r, l, link_bw, num_wavelengths_per_pair=1):
        NetworkTopology.__init__(self)
        self.name = "BCube" # BCube with EPS
        self.switch_radix = r
        self.num_levels = l + 1
        assert(l >= 1)
        self.num_gpus_per_group = r # number of switches per group
        self.num_gpus = r ** (l+1) # total number of switches in the topology
        self.num_groups = r ** l # number of base groups
        self.num_switches_in_level = [r ** level for level in range(self.num_levels)]
        self.num_wavelengths_per_pair = num_wavelengths_per_pair
        self.total_num_switches = (r ** l) * (l + 1)
        self.switches = [list(range(i*r**l,(i+1)*r**l)) for i in range(self.num_levels)] # these are nvswitches
        self.gpus = [x for x in range(self.total_num_switches, self.total_num_switches+self.num_gpus)]
        assert(self.total_num_switches == self.switches[-1][-1]+1)
        self.adjacency_matrix = [[0]*(self.num_gpus+self.total_num_switches) for _ in range((self.num_gpus+self.total_num_switches))]
        self.infiniband_link_bw = 200
        self.link_bw = link_bw # nvlink bandwidth
        self.link_latencies_ns = {"infiniband":400, "nvlink": 9000} # can also connect GPUs in each unit with NVSwitches + NVLinks

    def getNumServers(self):
        return self.num_gpus
    
    def getNumSwitches(self):
        return self.total_num_switches
    
    def getNumLinks(self):
        return self.total_num_switches * self.switch_radix

    def getNumTransceivers(self):
        return self.num_gpus * self.num_levels * 2

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
    
    def getName(self):
        network_name = self.name + "_{}r_{}l".format(self.num_gpus_per_group, self.num_levels-1)
        return network_name

    def getTopologyName(self):
        return "BCube"

    def getNumHostsPerSwitch(self):
        return 1

    def designIntraGroupTopology(self):
        # All GPUs connect to a non-blocking OCS which is effectively an all-to-all fullmesh
        self.gpu_groups = []
        for i in range(self.num_groups):
            self.gpu_groups.append(list(range(i*self.num_gpus_per_group, (i+1)*self.num_gpus_per_group)))
            switch_id = self.switches[0][i]
            for j in range(self.total_num_switches+i*self.num_gpus_per_group, self.total_num_switches+(i+1)*self.num_gpus_per_group):
                self.adjacency_matrix[j][switch_id] = self.num_wavelengths_per_pair
                self.adjacency_matrix[switch_id][j] = self.num_wavelengths_per_pair
    
    def designInterGroupTopology(self, level):
        # For a canonical design, for each level, connect all gpus in an alltoall fullmesh
        num_iteration = self.num_groups // self.num_switches_in_level[level]
        num_groups_per_iteration = len(self.gpu_groups) // num_iteration
        gpus_to_connect = []
        for i in range(num_iteration):
            group_list = [group for group in self.gpu_groups[i*num_groups_per_iteration:(i+1)*num_groups_per_iteration]]
            gpus_to_connect += self.connectSameIndexNodes(group_list)
        for i, gpus in enumerate(gpus_to_connect):
            switch_id = self.switches[level][i]
            for gpu in gpus:
                self.adjacency_matrix[self.total_num_switches+gpu][switch_id] = self.num_wavelengths_per_pair
                self.adjacency_matrix[switch_id][self.total_num_switches+gpu] = self.num_wavelengths_per_pair
        self.gpu_groups = [list(itertools.chain.from_iterable(self.gpu_groups[i*num_groups_per_iteration:(i+1)*num_groups_per_iteration])) for i in range(num_iteration)]
        return
    
    def connectSameIndexNodes(self, group_list):
        # group_list is a list of lists with same length
        # this function connects the nodes of the same index in each of the lists in a full mesh
        num_gpus_per_group = len(group_list[0])
        res = []
        for gpu_id in range(num_gpus_per_group):
            group = []
            for src_group_id in range(len(group_list)):
                src_gpu = group_list[src_group_id][gpu_id]
                group.append(src_gpu)
                for dst_group_id in range(src_group_id+1, len(group_list)):
                    dst_gpu = group_list[dst_group_id][gpu_id]
                    assert(src_group_id != dst_group_id and src_gpu != dst_gpu)
                    group.append(dst_gpu)
            res.append(group)
        return res
    
    def wireNetwork(self):
        print("[Setup] Wiring BCube network.")
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
        # Need to add dummy switch in order for Netbench to run
        # prefix += "Switches=set({})\n".format(self.dummy_switch) # For the aggregation switches only
        prefix += "ToRs=incl_range({},{})\n".format(self.switches[0][0], self.switches[-1][-1])
        prefix += "Servers=incl_range({},{})\n".format(self.gpus[0], self.gpus[-1])
        prefix += ("Switches=set()\n\n")
        return prefix + topol_str
    
    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        number_of_flows = 0
        offset = self.total_num_switches
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            assert(src in self.adjacency_list and dst in self.adjacency_list)
            if src != dst:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src+offset), int(dst+offset), sum_bytes)
                number_of_flows += 1
        return str_builder, number_of_flows

    def checkLinkAdjacencyList(self, src, dst):
        if src in self.adjacency_list and dst in self.adjacency_list:
            if dst in self.adjacency_list[src] and src in self.adjacency_list[dst]: return True
            else: return False
        else: return False

    def generateLinkDelayFileString(self):
        str_builder = ""    
        for src_gpu in self.gpus:
            for connected_device in self.adjacency_list[src_gpu]:
                assert(self.checkLinkAdjacencyList(src_gpu, connected_device)), "Link between {} and {} does not exist.".format(src_gpu, connected_device)
                if connected_device in self.switches[0]: # if connected to level 0 nvswitches
                    # str_builder += "{},{},{},{}\n".format(src_gpu, connected_device, self.link_latencies_ns["nvlink"], self.link_bw)
                    # str_builder += "{},{},{},{}\n".format(connected_device, src_gpu, self.link_latencies_ns["nvlink"], self.link_bw)
                    str_builder += "{},{},{},{}\n".format(src_gpu, connected_device, self.link_latencies_ns["infiniband"], self.link_bw)
                    str_builder += "{},{},{},{}\n".format(connected_device, src_gpu, self.link_latencies_ns["infiniband"], self.link_bw)
                else: # if connected to infiniband switches
                    # str_builder += "{},{},{},{}\n".format(src_gpu, connected_device, self.link_latencies_ns["infiniband"], self.infiniband_link_bw)
                    str_builder += "{},{},{},{}\n".format(src_gpu, connected_device, self.link_latencies_ns["infiniband"], self.link_bw)
        return str_builder
