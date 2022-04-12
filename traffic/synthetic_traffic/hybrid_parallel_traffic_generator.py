'''
Generates hybrid parallel traffic.
'''

from traffic.synthetic_traffic import synthetic_traffic_generator
from traffic.synthetic_traffic import sipco_allgather_traffic_generator, sipco_allreduce_traffic_generator, sipco_alltoall_traffic_generator
from traffic.synthetic_traffic import ring_allgather_traffic_generator, ring_allreduce_traffic_generator, ring_alltoall_traffic_generator
from traffic.synthetic_traffic import hierarchical_allgather_traffic_generator, hierarchical_allreduce_traffic_generator, hierarchical_alltoall_traffic_generator
from traffic.synthetic_traffic import mesh_allreduce_traffic_generator, mesh_alltoall_traffic_generator
from traffic.synthetic_traffic import primitive_alltoall_traffic_generator

class HybridParallelTrafficGenerator(synthetic_traffic_generator.SyntheticTrafficGenerator):
    # Model parallel within group, data parallel across groups
    def __init__(self, p, num_mp_nodes, model_info):
        synthetic_traffic_generator.SyntheticTrafficGenerator.__init__(self, p=p)
        self.num_nodes = p
        self.num_mp_nodes = num_mp_nodes
        self.num_dp_nodes = self.num_nodes // self.num_mp_nodes
        self.num_mp_groups = self.num_dp_nodes
        assert(self.num_nodes == self.num_mp_nodes * self.num_dp_nodes), "num nodes: {}, num_mp_nodes: {}, num_dp_nodes: {}".format(self.num_nodes, self.num_mp_nodes, self.num_dp_nodes)
        self.model_info = model_info
        self.intra_group_comm_type = model_info["intra_group_comm_type"]
        self.inter_group_comm_type = model_info["inter_group_comm_type"]
        self.intra_group_algo_type = model_info["intra_group_algo_type"]
        self.inter_group_algo_type = model_info["inter_group_algo_type"]
        self.intra_group_message_size = model_info["intra_group_message_size"]
        self.inter_group_message_size = model_info["inter_group_message_size"]
        self.name = "hybrid_parallel"
        return

    def generateTrafficCommType(self, comm_type, algo_type, message_size, comm_data:dict):
        traffic_generator = None
        traffic_events = []
        p = comm_data['p']
        r, l = (comm_data["r"], comm_data["l"]) if algo_type == "sipco" else (None, None)
        if comm_type == "ALLTOALL":
            if algo_type == "sipco":
                traffic_generator = sipco_alltoall_traffic_generator.SiPCOAllToAllTrafficGenerator(r, l, p)
            elif algo_type == "ring":
                traffic_generator = ring_alltoall_traffic_generator.RingAllToAllTrafficGenerator(p, p)
            elif algo_type == "hierarchical":
                traffic_generator = hierarchical_alltoall_traffic_generator.HierarchicalAllToAllTrafficGenerator(p, int(p ** (1/2)), p)
            elif algo_type == "primitive":
                traffic_generator = primitive_alltoall_traffic_generator.PrimitiveAllToAllTrafficGenerator(p)
            elif algo_type == "mesh":
                traffic_generator = mesh_alltoall_traffic_generator.MeshAllToAllTrafficGenerator(p, p)
        elif comm_type == "ALLGATHER":
            if algo_type == "sipco":
                traffic_generator = sipco_allgather_traffic_generator.SiPCOAllGatherTrafficGenerator(r,l,p)
            elif algo_type == "ring":
                traffic_generator = ring_allgather_traffic_generator.RingAllGatherTrafficGenerator(p, p)
            elif algo_type == "hierarchical":
                traffic_generator = hierarchical_allgather_traffic_generator.HierarchicalAllGatherTrafficGenerator(p, int(p ** (1/2)), p)
        elif comm_type == "ALLREDUCE":
            if algo_type == "sipco":
                traffic_generator = sipco_allreduce_traffic_generator.SiPCOAllReduceTrafficGenerator(r, l, p)
            elif algo_type == "ring":
                traffic_generator = ring_allreduce_traffic_generator.RingAllReduceTrafficGenerator(p, p)
            elif algo_type == "hierarchical":
                traffic_generator = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p, int(p ** (1/2)), p)
            elif algo_type == "mesh":
                traffic_generator = mesh_allreduce_traffic_generator.MeshAllReduceTrafficGenerator(p, int(p ** (1/2)), p)
        if traffic_generator: 
            traffic_events = traffic_generator.plan_arrivals(message_size, 0)
        return traffic_events

    def map_traffic_events(self, unmapped_traffic, nodes_to_map, start_time):
        # unmapped traffic should contain a continuous block of nodes
        min_node, max_node = float('inf'), -float("inf")
        for (_, src, dst, _) in unmapped_traffic:
            if min(src, dst) < min_node: min_node = min(src, dst)
            if max(src, dst) > max_node: max_node = max(src, dst)
        assert(max_node - min_node + 1 == len(nodes_to_map))
        node_map = {}
        for i, node in enumerate(range(min_node, max_node+1)):
            node_map[node] = nodes_to_map[i]
        traffic_events_new = []
        for (st, src,dst, fs) in unmapped_traffic:
            new_src, new_dst = node_map[src], node_map[dst]
            traffic_events_new.append((st+start_time, new_src, new_dst, fs))
        return traffic_events_new

    def plan_arrivals(self,total_message_size, start_time=0):
        assert(total_message_size==0), "Make sure we are not using the passed in message size!"
        traffic_arrival_events = []
        start_time = start_time
        mp_groups = [list(range(m*self.num_mp_nodes, (m+1)*self.num_mp_nodes)) for m in range(self.num_mp_groups)]
        dp_groups = self.findCommunicatingNodes(mp_groups)
        
        # intra mp_group alltoall - model parallel 
        for mp_group in mp_groups:
            traffic_events = self.generateTrafficForNodeGroup(mp_group, "intra", start_time)
            traffic_arrival_events += traffic_events
        traffic_arrival_events.sort(key=lambda x: x[0])
        
        # inter mp_group allreduce -- data parallel
        start_time = traffic_arrival_events[-1][0] + 1
        for dp_group in dp_groups:
            traffic_events = self.generateTrafficForNodeGroup(dp_group, "inter", start_time)
            traffic_arrival_events += traffic_events
        traffic_arrival_events.sort(key=lambda x: (x[0], x[1]))
        return traffic_arrival_events

    def generateTrafficForNodeGroup(self, group, group_type, start_time):
        group_type_map = {"intra": [self.intra_group_comm_type, self.intra_group_algo_type, self.intra_group_message_size],
                          "inter": [self.inter_group_comm_type, self.inter_group_algo_type, self.inter_group_message_size]}
        comm_data = dict({"p": len(group)})
        if group_type_map[group_type][1] == "sipco":
            # determine how many levels does each MP group cover
            l = self.model_info["l"]
            r = self.model_info["r"]
            assert(r ** (l+1) == self.num_nodes)
            assert(self.num_mp_nodes % r == 0 and self.num_nodes % self.num_mp_nodes == 0)
            num_levels = l + 1
            num_switches_in_level = [r ** level for level in range(num_levels)]
            if group_type == "intra":
                num_group_per_mp = self.num_mp_nodes // r
                algo_level = 0
                while num_group_per_mp > num_switches_in_level[algo_level]:
                    algo_level += 1
                # if num_group_per_mp == 1: # consider the case for < 1
                comm_data["l"] = algo_level
                comm_data["r"] = r
                # elif num_group_per_mp > 1:
                #     comm_data["r"] = r // 2 # reduce the dimension to utilize more directly connected links
                #     comm_data["l"] = int(math.log2(comm_data["p"]) // (math.log2(comm_data["r"])) - 1)
                #     # print(comm_data["l"])
                #     # print(comm_data["r"])
                #     assert(comm_data["p"] == comm_data["r"] ** (comm_data["l"]+1)), "p{},r{},l{}".format(comm_data["p"],comm_data["r"],comm_data["l"])
                # sys.exit()
            elif group_type == "inter":
                # Cannot guarantee one-hop direct bandwidth
                # need to resort to other ECMP paths
                comm_data["l"] = 0
                comm_data["r"] = comm_data["p"]
            else:
                raise Exception("[Error] Incorrect group type.")
        traffic_events = self.generateTrafficCommType(group_type_map[group_type][0], group_type_map[group_type][1], group_type_map[group_type][2], comm_data)
        traffic_events = self.map_traffic_events(traffic_events, group, start_time)
        return traffic_events

    def findCommunicatingNodes(self, group_list):
        if len(group_list) == 1: return group_list
        num_gpus_per_group = len(group_list[0])
        communicating_nodes = [[group[i] for group in group_list] for i in range(num_gpus_per_group)]
        return communicating_nodes