from network_topology.network_topology import *

class FatTreeCustomizedNetworkTopology(NetworkTopology):
    def __init__(self, eps_radix, target_num_servers, link_bw, num_layers=3, oversubscription_ratio=(1,1)):
        NetworkTopology.__init__(self)
        self.k = eps_radix 
        self.num_layers = num_layers
        self.target_num_servers = target_num_servers
        self.oversubscription_ratio = oversubscription_ratio
        self.aggregation_to_core_link_ratio = 1
        self.num_core_switches = (self.k//2)**2
        self.num_aggregation_switches_per_pod = self.k // 2
        self.num_tor_switches_per_pod = self.k // 2
        self.num_servers_per_tor = self.k // 2
        self.num_servers_per_pod = (self.k//2)**2
        assert(self.target_num_servers >= self.num_servers_per_pod and self.target_num_servers % self.num_servers_per_pod == 0), "{},{}".format(self.target_num_servers,self.num_servers_per_pod)
        self.num_pods = self.target_num_servers // self.num_servers_per_pod
        assert(self.target_num_servers <= self.num_servers_per_pod * self.num_pods)
        self.total_num_aggregation_switches = self.num_pods * self.num_aggregation_switches_per_pod
        self.total_num_tor_switches = self.num_pods * self.num_tor_switches_per_pod
        self.total_num_servers = self.num_servers_per_pod * self.num_pods
        self.total_num_switches = self.num_core_switches + self.total_num_aggregation_switches + self.total_num_tor_switches
        self.total_num_nodes = self.total_num_switches + self.total_num_servers
        self.num_links_from_tor_to_aggregation = int(self.k//2 * (float(self.oversubscription_ratio[1]) / float(self.oversubscription_ratio[0]))) # per tor-aggregation pair
        self.num_links_from_aggregation_to_core = int(self.num_aggregation_switches_per_pod * self.num_links_from_tor_to_aggregation // self.aggregation_to_core_link_ratio) # per core-aggregation pair
        self.topology_info = None
        self.is_rewired = False
        self.link_bw = link_bw
        assert(self.total_num_servers == self.target_num_servers)
        assert(self.num_servers_per_pod == self.num_servers_per_tor * self.num_tor_switches_per_pod)
    
    # Retrieves the name of this topology, summarizing some of the essential parameters. Used to create topology directory and filename.
    def getName(self):
        network_name = "fattree_customized_eps{}_ns{}_nl{}_{}to{}".format(self.eps_radix, self.target_num_servers, self.num_layers, int(self.oversubscription_ratio[0]), int(self.oversubscription_ratio[1]))
        return network_name
    
    def getLinkBW(self):
        return self.link_bw
    
    def getLinks(self):
        links = []
        for src in self.adjacency_list.keys():
            for dst in self.adjacency_list[src]:
                links.append((src, dst))
        return links
    
    def getNumSwitches(self):
        return self.total_num_switches
    
    def getNumServers(self):
        return self.total_num_servers

    def getNumHostsPerSwitch(self):
        return self.num_servers_per_tor

    def wireNetwork(self):
        print("[Setup] Wiring fattree network.")
        # 3-level Fat-tree: core, aggregation, ToR
        self.core_switches = [0] # 1 Giant Core Switch Abstraction
        self.aggregation_layer_switches = list(range(1, self.num_pods+1)) # 1 Giant Aggregation Switch Per Pod
        self.ToR_layer_switches = []
        self.servers = []
        tor_switch_offset = len(self.core_switches) + len(self.aggregation_layer_switches)
        for pod_id in range(self.num_pods):
            start_node = tor_switch_offset + pod_id * (self.num_tor_switches_per_pod)
            end_node = tor_switch_offset + (pod_id+1) * (self.num_tor_switches_per_pod)
            self.ToR_layer_switches.append(list(range(start_node, end_node)))
        server_offset = tor_switch_offset + self.total_num_tor_switches
        for pod_id in range(self.num_pods):
            start_node = server_offset + pod_id * (self.num_servers_per_pod)
            end_node = server_offset + (pod_id+1) * (self.num_servers_per_pod)
            self.servers.append(list(range(start_node, end_node)))
        self.topology_info = {"Core": self.core_switches, "Aggregation": self.aggregation_layer_switches, "ToR":self.ToR_layer_switches, "Servers": self.servers}
        self.connectAdjacentLayers()
        self.check_all_radix_requirement()
        self.checkNetworkConnectivity()
        return

    def connectAdjacentLayers(self):
        # connect core and aggregation
        for pod_id in range(self.num_pods):
            aggregation_switch = self.aggregation_layer_switches[pod_id]
            if aggregation_switch not in self.adjacency_list: self.adjacency_list[aggregation_switch] = {}
            for core in self.core_switches:
                if core not in self.adjacency_list: self.adjacency_list[core] = {}
                self.adjacency_list[core][aggregation_switch] = max(1, self.num_links_from_aggregation_to_core)
                self.adjacency_list[aggregation_switch][core] = max(1, self.num_links_from_aggregation_to_core)
        # connect aggregation and ToR
        for pod_id in range(self.num_pods):
            aggregation_switch = self.aggregation_layer_switches[pod_id]
            ToR_switches = self.ToR_layer_switches[pod_id]
            for ToR in ToR_switches:
                if ToR not in self.adjacency_list: self.adjacency_list[ToR] = {}
                self.adjacency_list[aggregation_switch][ToR] = max(1, self.num_links_from_tor_to_aggregation)
                self.adjacency_list[ToR][aggregation_switch] = max(1, self.num_links_from_tor_to_aggregation)
        # connect ToR to servers
        for pod_id in range(self.num_pods):
            ToR_switches = self.ToR_layer_switches[pod_id]
            servers = self.servers[pod_id]
            server_index = 0
            for ToR in ToR_switches:
                for _ in range(self.num_servers_per_tor):
                    server = servers[server_index]
                    if server not in self.adjacency_list: self.adjacency_list[server] = {}
                    self.adjacency_list[ToR][server] = 1
                    self.adjacency_list[server][ToR] = 1
                    server_index += 1
    
    def checkTaperingRatio(self):
        # checks the relative tapering between aggregation layer and core layer
        total_num_aggregation_links_per_pod = sum([sum(self.adjacency_list[aggregation].values()) for aggregation in self.aggregation_layer_switches]) // self.num_pods
        total_num_core_links_per_pod = sum([sum(self.adjacency_list[core].values()) for core in self.core_switches]) // self.num_pods
        assert((total_num_aggregation_links_per_pod - total_num_core_links_per_pod) == self.aggregation_to_core_link_ratio * total_num_core_links_per_pod)

    def checkCoreRadixRequirement(self):
        for core in self.core_switches:
            # print(self.num_links_from_aggregation_to_core, self.num_pods)
            # print(sum(self.adjacency_list[core].values()), self.num_links_from_aggregation_to_core * self.num_pods)
            assert(sum(self.adjacency_list[core].values()) == self.num_links_from_aggregation_to_core * self.num_pods)
    
    def checkAggregationRadixRequirement(self):
        for aggregation in self.aggregation_layer_switches:
            target_num_links = (self.k//2 * self.oversubscription_ratio[1] / self.oversubscription_ratio[0]) * self.num_aggregation_switches_per_pod + self.num_links_from_aggregation_to_core
            assert(int(sum((self.adjacency_list[aggregation].values()))) == int(target_num_links)), "{},{},{}".format(aggregation,int(sum((self.adjacency_list[aggregation].values()))), int(target_num_links))

    def checkTorsRadixRequirement(self):
        for tors in self.ToR_layer_switches:
            for tor in tors:
                target_num_links = (self.k // 2 + self.k//2 * (float(self.oversubscription_ratio[1]) / float(self.oversubscription_ratio[0])))
                assert(sum(self.adjacency_list[tor].values()) == int(target_num_links))
    
    def checkServersRadixRequirement(self):
        for servers in self.servers:
            for server in servers:
                assert(len(self.adjacency_list[server].keys()) == 1)
            
    def check_all_radix_requirement(self):
        self.checkCoreRadixRequirement()
        self.checkAggregationRadixRequirement()
        self.checkTorsRadixRequirement()
        self.checkServersRadixRequirement()

    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        virtual_servers_offset = self.servers[0][0] # pass over aggregation + ToR switches to get to the servers
        number_of_flows = 0
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            src_virtual = virtual_servers_offset + src
            dst_virtual = virtual_servers_offset + dst
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list), "{},{}".format(src_virtual, dst_virtual)
            if src_virtual != dst_virtual:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src_virtual), int(dst_virtual), int(sum_bytes))
                number_of_flows += 1
        return str_builder, number_of_flows

    # Generates the traffic events in the form of strings.
    def generate_traffic_events_string_from_probability(self, traffic_probability):
        str_builder = ""
        virtual_servers_offset = self.num_pods * (1 + self.num_tor_switches_per_pod)
        num_servers_per_tor = self.eps_radix / 2
        index = 0
        prob_sum = 0
        for src, dst in traffic_probability:
            src_virtual = int(virtual_servers_offset + src // num_servers_per_tor)
            dst_virtual = int(virtual_servers_offset + dst // num_servers_per_tor)
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list)
            if src_virtual != dst_virtual:
                prob_sum += traffic_probability[(src, dst)]
        for src, dst in traffic_probability:
            src_virtual = int(virtual_servers_offset + src // num_servers_per_tor)
            dst_virtual = int(virtual_servers_offset + dst // num_servers_per_tor)
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list)
            if src_virtual != dst_virtual:
                str_builder += "{},{},{},{:.4e}\n".format(index, src_virtual, dst_virtual, traffic_probability[(src, dst)] / prob_sum)
                index += 1
        return str_builder


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
        prefix += "ToRs=incl_range({},{})\n".format(self.ToR_layer_switches[0][0], self.ToR_layer_switches[-1][-1])
        prefix += "Servers=incl_range({},{})\n".format(self.servers[0][0], self.servers[-1][-1])
        core_switches = [str(x) for x in self.core_switches]
        aggregation_switches = [str(x) for x in self.aggregation_layer_switches]
        prefix += "Switches=set({},{})\n".format(",".join(core_switches), ",".join(aggregation_switches))
        return prefix + topol_str