from network_topology.network_topology import *


class Dragonfly(NetworkTopology):
    def __init__(self, G, A, h, link_bw, concentration=1):
        NetworkTopology.__init__(self)
        self.name = "dragonfly"
        self.num_groups = G # number of groups
        self.num_switches = A # number of switches per group
        self.num_interpod_links_per_switch = h # number of interpod links per switch
        self.concentration_factor = concentration # number of host servers per switch
        self.total_num_switches = G * A # total number of switches in the topology
        self.num_hosts_per_pod = self.num_switches * self.concentration_factor
        self.total_num_hosts = self.num_hosts_per_pod * self.num_groups 
        self.adjacency_matrix = None
        self.link_bw = link_bw
        self.interpod_links = []
        self.intrapod_links = []

    def getNumServers(self):
        return self.total_num_switches * self.concentration_factor

    def getLinkBW(self):
        return self.link_bw
    
    def getNumSwitches(self):
        return self.total_num_switches
    
    def getAdjacencyMatrix(self):
        return self.adjacency_matrix
    
    def getName(self):
        network_name = self.name + "_{}g_{}a_{}h_{}p".format(self.num_groups, self.num_switches, self.num_interpod_links_per_switch, self.concentration_factor)
        return network_name
    
    def getNumHostsPerSwitch(self):
        return self.concentration_factor
    
    def designIntraGroupTopology(self):
        # adjacency matrix is only for switches; servers will be added later
        self.adjacency_matrix = [0] * self.total_num_switches
        for switch in range(self.total_num_switches):
            self.adjacency_matrix[switch] = [0] * self.total_num_switches
        #first design the intragroup matrix in the full topology
        for i in range(self.num_groups):
            for row in range(i * self.num_switches, (i+1) * self.num_switches):
                for col in range(row+1, (i+1) * self.num_switches):
                    if row != col:
                        self.adjacency_matrix[row][col] = 1
                        self.adjacency_matrix[col][row] = 1
                        self.intrapod_links.append((row,col))

    # Non-canonical Dragonfly with potentially non-even distribution of links without any randomness
    # note: if num_intergroup_links_per_group is odd, then there will be a group with num_intergroup_links_per_group-1 interpod links
    def designGroupLevelTopology(self):
        num_intergroup_links_per_group = self.num_switches * self.num_interpod_links_per_switch
        eta = [[0]*self.num_groups for _ in range(self.num_groups)]
        for i in range(self.num_groups):
            for d in range(num_intergroup_links_per_group):
                mu = [num_intergroup_links_per_group+1] * self.num_groups
                for j in range(self.num_groups):
                    if i == j: continue
                    mu[j] = sum(eta[j])
                k = mu.index(min(mu))
                if i != k and sum(eta[k]) < num_intergroup_links_per_group and sum(eta[i]) < num_intergroup_links_per_group:
                    eta[i][k] += 1
                    eta[k][i] += 1
        return eta

    def designFullTopology(self):
        self.designIntraGroupTopology()
        eta = self.designGroupLevelTopology()
        for i in range(len(eta)):
            for j in range(i+1, len(eta[i])):
                while eta[i][j] != 0:
                    src, dst = self.findAvailableSrcDst(i,j)
                    eta[i][j] -= 1
                    self.adjacency_matrix[src][dst] += 1
                    self.adjacency_matrix[dst][src] += 1
                    self.interpod_links.append((src,dst))
    
    def wireNetwork(self):
        print("[Setup] Wiring dragonfly network.")
        # first wire all the switches
        self.designFullTopology()
        assert(self.total_num_switches == len(self.adjacency_matrix))
        # then wire the servers
        self.tors = []
        self.servers = []
        server_id_offset = self.total_num_switches
        for src in range(len(self.adjacency_matrix)):
            self.tors.append(src)
            self.adjacency_list[src] = {}
            # add destination switches
            for dst in range(len(self.adjacency_matrix[src])):
                if self.adjacency_matrix[src][dst] != 0:
                    self.adjacency_list[src][dst] = self.adjacency_matrix[src][dst]
            # add destination servers (one server is only connected to one switch)
            for server_id in range(self.concentration_factor):
                server = server_id + server_id_offset
                self.servers.append(server)
                self.adjacency_list[server] = {}
                self.adjacency_list[src][server] = 1
                self.adjacency_list[server][src] = 1
            server_id_offset += self.concentration_factor
    
    def findAvailableSrcDst(self, i, j):
        src_group = i
        src_group_switches = range(src_group * self.num_switches, (src_group+1) * self.num_switches)
        src_mu = []
        for src_switch in src_group_switches:
            src_mu.append(sum(self.adjacency_matrix[src_switch]))
        src = src_mu.index(min(src_mu)) + (src_group) * self.num_switches
        dst_group = j
        dst_group_switches = range(dst_group * self.num_switches, (dst_group+1) * self.num_switches)
        dst_mu = []
        for dst_switch in dst_group_switches:
            dst_mu.append(sum(self.adjacency_matrix[dst_switch]))
        dst = dst_mu.index(min(dst_mu)) + (dst_group) * self.num_switches
        return src, dst
    
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
        # prefix += "Switches=incl_range({},{})\n".format(self.ocs[0], self.ocs[-1]) # For the aggregation switches only
        prefix += "ToRs=incl_range({},{})\n".format(self.tors[0], self.tors[-1])
        prefix += "Servers=incl_range({},{})\n".format(self.servers[0], self.servers[-1])
        prefix += ("Switches=set()\n\n")
        return prefix + topol_str
    
    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        virtual_servers_offset = self.total_num_switches
        num_servers_per_tor = self.concentration_factor
        number_of_flows = 0
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            src_virtual = virtual_servers_offset + src // num_servers_per_tor
            dst_virtual = virtual_servers_offset + dst // num_servers_per_tor
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list), "{},{}".format(src_virtual,dst_virtual)
            if src_virtual != dst_virtual:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src_virtual), int(dst_virtual), sum_bytes)
                number_of_flows += 1
        return str_builder, number_of_flows