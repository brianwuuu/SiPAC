import math, pprint
import os, sys
from network_topology.network_topology import *


class DGX_Superpod(NetworkTopology):
    # 1) NVIDIA DGX SuperPOD: Scalable Infrastructure for AI Leadership
    # 2) https://www.microway.com/preconfiguredsystems/nvidia-dgx-a100/?gclid=CjwKCAiAsNKQBhAPEiwAB-I5zSDFlAzweRTnv0GULrFRsg5FnEFWMkIaAUaOA_gFPqltrb0J7BIbBRoCTt8QAvD_BwE
    def __init__(self, target_num_gpus, link_bw):
        NetworkTopology.__init__(self)
        self.name = "dgx_superpod"
        # Counting neetwork devices 
        self.num_gpus_per_dgx = 8
        self.num_nv_switches_per_dgx = 6
        self.num_pcie_switches_per_dgx = 4
        self.num_dgx_per_scalable_unit = 20
        self.num_leaf_switch_per_scalable_unit = 8
        self.num_leaf_switch_per_pcie_switch = 2
        self.target_num_gpus = target_num_gpus
        self.num_dgx = math.ceil(self.target_num_gpus / self.num_gpus_per_dgx)
        self.total_num_gpus = self.num_dgx * self.num_gpus_per_dgx
        self.num_scalable_units = max(1, math.ceil(self.num_dgx / self.num_dgx_per_scalable_unit))
        self.num_leaf_switches = math.ceil(self.num_scalable_units * self.num_leaf_switch_per_scalable_unit)
        self.num_spine_switches = self.num_leaf_switches // 2 # follow the ratio of 2:1
        assert(self.target_num_gpus >= self.num_gpus_per_dgx)
        assert(self.total_num_gpus >= self.target_num_gpus)
        # Switches
        self.spine_switches = list(range(self.num_spine_switches))
        self.leaf_switches = list(range(self.num_spine_switches, self.num_spine_switches+self.num_leaf_switches))
        self.pcie_offset = self.num_spine_switches + self.num_leaf_switches
        self.pcie_switches = [list(range(self.pcie_offset+i*self.num_pcie_switches_per_dgx, self.pcie_offset+(i+1)*self.num_pcie_switches_per_dgx)) for i in range(self.num_dgx)]
        self.nvswitch_offset = self.pcie_offset + self.num_pcie_switches_per_dgx * self.num_dgx
        self.nv_switches = [list(range(self.nvswitch_offset+i*self.num_nv_switches_per_dgx, self.nvswitch_offset+(i+1)*self.num_nv_switches_per_dgx)) for i in range(self.num_dgx)]
        self.total_num_switches = self.num_spine_switches + self.num_leaf_switches + self.num_dgx * (self.num_pcie_switches_per_dgx + self.num_nv_switches_per_dgx)
        # Computing nodes
        self.gpu_offset = self.pcie_offset + (self.num_pcie_switches_per_dgx + self.num_nv_switches_per_dgx) * self.num_dgx
        self.gpus = [list(range(self.gpu_offset+i*self.num_gpus_per_dgx, self.gpu_offset+(i+1)*self.num_gpus_per_dgx)) for i in range(self.num_dgx)]
        self.total_num_nodes = self.total_num_gpus + self.total_num_switches
        # Links
        # Infiniband : pcie : nvlink = 200Gbps : 32 * 8 Gbps : 2 * 25 * 8 Gbps = 200 Gbps : 256 Gbps : 400 Gbps = 0.5 : 0.64 : 1
        self.nvlink_bw = link_bw
        self.pcie_link_bw = 32 * 8
        self.infiniband_link_bw = 200
        self.link_latencies_ns = {"ib_spine": 400, "ib_leaf": 130, "pcie": 110, "nvlink": 9000}
        # Adjacency Matrix
        self.adjacency_matrix = [[0]*self.total_num_nodes for _ in range(self.total_num_nodes)]

    def getNumServers(self):
        return self.total_num_gpus
    
    def getName(self):
        network_name = self.name + "_{}nodes".format(self.total_num_gpus)
        return network_name
    
    def getNumSwitches(self):
        return self.total_num_switches
    
    def getTopologyName(self):
        return "DGX-SuperPod"
    
    def getLinkBW(self):
        return self.nvlink_bw
    
    def getNumNVLinks(self):
        self.num_nvlinks_per_dgx = self.num_gpus_per_dgx * self.num_nv_switches_per_dgx
        return self.num_nvlinks_per_dgx * self.num_dgx
    
    def getNumTransceivers(self):
        num_gpu_leaf_transceivers = self.num_gpus_per_dgx * self.num_dgx * 2 # both ends
        num_leaf_spine_transceivers = self.num_leaf_switches * self.num_spine_switches * 2
        return num_gpu_leaf_transceivers + num_leaf_spine_transceivers
    
    def getNetworkInfo(self):
        print("Number of GPUs: ", self.total_num_gpus)
        print("Number of DGXes: ", self.num_dgx)
        print("Number of PCIe Switches: ", self.num_pcie_switches_per_dgx * self.num_dgx)
        print("Number of Leaf Switches: ", self.num_leaf_switches)
        print("Number of Spine Switches: ", self.num_spine_switches)
        print("Number of NVSwitches: ", self.num_nv_switches_per_dgx * self.num_dgx)
        print("Spine Switches: ", self.spine_switches)
        print("Leaf Switches: ", self.leaf_switches)
        print("PCIe Switches: ", self.pcie_switches)
        print("NVSwitches: ", self.nv_switches)
        print("GPUs: ", self.gpus)
        print("Network Topology: ")
        pprint.pprint(self.adjacency_list)
    
    def designIntraDGXTopology(self, group_id):
        # DGX-2 Intra-node Topology
        # Each GPU is ocnnected to every NVSwitch within the DGX
        for gpu in self.gpus[group_id]:
            for nvswitch in self.nv_switches[group_id]:
                self.adjacency_matrix[gpu][nvswitch] = 1
                self.adjacency_matrix[nvswitch][gpu] = 1
        starting_gpu = self.gpus[group_id][0]
        starting_pcie_switch = self.pcie_switches[group_id][0]
        # Finally add the connections to the pcie switches with
        self.adjacency_matrix[starting_gpu][starting_pcie_switch] = 1
        self.adjacency_matrix[starting_pcie_switch][starting_gpu] = 1
        self.adjacency_matrix[starting_gpu+7][starting_pcie_switch] = 1
        self.adjacency_matrix[starting_pcie_switch][starting_gpu+7] = 1
        self.adjacency_matrix[starting_gpu+1][starting_pcie_switch+1] = 1
        self.adjacency_matrix[starting_pcie_switch+1][starting_gpu+1] = 1
        self.adjacency_matrix[starting_gpu+6][starting_pcie_switch+1] = 1
        self.adjacency_matrix[starting_pcie_switch+1][starting_gpu+6] = 1
        self.adjacency_matrix[starting_gpu+2][starting_pcie_switch+2] = 1
        self.adjacency_matrix[starting_pcie_switch+2][starting_gpu+2] = 1
        self.adjacency_matrix[starting_gpu+5][starting_pcie_switch+2] = 1
        self.adjacency_matrix[starting_pcie_switch+2][starting_gpu+5] = 1
        self.adjacency_matrix[starting_gpu+3][starting_pcie_switch+3] = 1
        self.adjacency_matrix[starting_pcie_switch+3][starting_gpu+3] = 1
        self.adjacency_matrix[starting_gpu+4][starting_pcie_switch+3] = 1
        self.adjacency_matrix[starting_pcie_switch+3][starting_gpu+4] = 1
        
    def connectDGXToLeafSwitches(self):
        for su_id in range(self.num_scalable_units):
            leaf_switches = self.leaf_switches[(su_id)*self.num_leaf_switch_per_scalable_unit:(su_id+1)*self.num_leaf_switch_per_scalable_unit]
            pcie_switch_group = self.pcie_switches[su_id*self.num_dgx_per_scalable_unit:(su_id+1)*self.num_dgx_per_scalable_unit]
            for pcie_switches in pcie_switch_group:
                slow_pt = fast_pt = 0
                while fast_pt != len(leaf_switches) and slow_pt != len(pcie_switches):
                    leaf_switch, pcie_switch = leaf_switches[fast_pt], pcie_switches[slow_pt]
                    self.adjacency_matrix[leaf_switch][pcie_switch] = 1
                    self.adjacency_matrix[pcie_switch][leaf_switch] = 1
                    self.adjacency_matrix[leaf_switch+1][pcie_switch] = 1
                    self.adjacency_matrix[pcie_switch][leaf_switch+1] = 1
                    fast_pt += 2
                    slow_pt += 1
                assert(fast_pt == self.num_leaf_switch_per_pcie_switch * slow_pt)
            
    
    def connectLeafToSpineSwitches(self):
        for spine_switch in self.spine_switches:
            for leaf_switch in self.leaf_switches:
                self.adjacency_matrix[spine_switch][leaf_switch] = 1
                self.adjacency_matrix[leaf_switch][spine_switch] = 1

    def wireNetwork(self):
        print("[Setup] Wiring DGX_Superpod network.")
        for group_id in range(self.num_dgx):
            self.designIntraDGXTopology(group_id)
        self.connectDGXToLeafSwitches()
        self.connectLeafToSpineSwitches()
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
        num_nodes = len(self.adjacency_list)
        assert(self.total_num_nodes == num_nodes)
        prefix += ("|V|={}".format(num_nodes) + "\n")
        prefix += ("|E|={}".format(num_edges) + "\n")
        #  Switches include spine, leaf switches
        prefix += "Switches=incl_range({},{})\n".format(self.spine_switches[0], self.leaf_switches[-1])
        # ToRs and servers both include pcie switches and gpus
        prefix += "ToRs=incl_range({},{})\n".format(self.pcie_switches[0][0], self.nv_switches[-1][-1])
        prefix += "Servers=incl_range({},{})\n\n".format(self.gpus[0][0], self.gpus[-1][-1])
        return prefix + topol_str
    
    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        virtual_servers_offset = self.total_num_switches
        number_of_flows = 0
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            src_virtual = virtual_servers_offset + src
            dst_virtual = virtual_servers_offset + dst
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list), "{},{}".format(src_virtual,dst_virtual)
            if src_virtual != dst_virtual:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src_virtual), int(dst_virtual), sum_bytes)
                number_of_flows += 1
        return str_builder, number_of_flows
    
    def checkLinkAdjacencyList(self, src, dst):
        if src in self.adjacency_list and dst in self.adjacency_list:
            if dst in self.adjacency_list[src] and src in self.adjacency_list[dst]: return True
            else: return False
        else: return False
    
    def generateLinkDelayFileString(self):
        str_builder = ""
        # 1) generate link delay between spine and leaf
        for spine_switch in self.spine_switches:
            for leaf_switch in self.leaf_switches:
                assert(self.checkLinkAdjacencyList(spine_switch, leaf_switch)), "Link between {} and {} does not exist.".format(spine_switch, leaf_switch)
                str_builder += "{},{},{},{}\n".format(spine_switch, leaf_switch, self.link_latencies_ns["ib_spine"], self.infiniband_link_bw)
                str_builder += "{},{},{},{}\n".format(leaf_switch, spine_switch, self.link_latencies_ns["ib_spine"], self.infiniband_link_bw)
        
        # 2) generate link delay between leaf and pcie switches
        for leaf_switch in self.leaf_switches:
            for connected_switch in self.adjacency_list[leaf_switch]:
                if connected_switch in range(self.pcie_switches[0][0], self.pcie_switches[-1][-1]+1):
                    assert(self.checkLinkAdjacencyList(connected_switch, leaf_switch)), "Link between {} and {} does not exist.".format(connected_switch, leaf_switch)
                    str_builder += "{},{},{},{}\n".format(connected_switch, leaf_switch, self.link_latencies_ns["ib_leaf"], self.infiniband_link_bw)
                    str_builder += "{},{},{},{}\n".format(leaf_switch, connected_switch, self.link_latencies_ns["ib_leaf"], self.infiniband_link_bw)
                
        # 3) generate link delay between pcie switches and gpus
        for pcie_switch_group in self.pcie_switches:
            for pcie_switch in pcie_switch_group:
                for connected_device in self.adjacency_list[pcie_switch]:
                    if connected_device in range(self.gpus[0][0], self.gpus[-1][-1]+1):
                        assert(self.checkLinkAdjacencyList(connected_device, pcie_switch)), "Link between {} and {} does not exist.".format(connected_device, pcie_switch)
                        str_builder += "{},{},{},{}\n".format(connected_device, pcie_switch, self.link_latencies_ns["pcie"], self.pcie_link_bw)
                        str_builder += "{},{},{},{}\n".format(pcie_switch, connected_device, self.link_latencies_ns["pcie"], self.pcie_link_bw)
                    
        # 4) generate link delay between gpus and nvswitches
        for gpu_group in self.gpus:
            for src_gpu in gpu_group:
                for connected_device in self.adjacency_list[src_gpu]:
                    if connected_device in range(self.nv_switches[0][0], self.nv_switches[-1][-1]+1):
                        assert(self.checkLinkAdjacencyList(src_gpu, connected_device)), "Link between {} and {} does not exist.".format(src_gpu, connected_device)
                        str_builder += "{},{},{},{}\n".format(src_gpu, connected_device, self.link_latencies_ns["nvlink"], self.nvlink_bw)
        return str_builder