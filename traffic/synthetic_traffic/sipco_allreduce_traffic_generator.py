import itertools, math
from .synthetic_traffic_generator import *

'''
Generates SiPCO allreduce traffic.
'''
class SiPCOAllReduceTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, r, l, num_server_per_job, num_repetitions=2):
        SyntheticTrafficGenerator.__init__(self, p = r ** (l + 1))
        self.num_levels = l + 1
        self.num_servers = r ** (l + 1)
        self.num_groups = r ** l
        self.num_switches_in_level = [r ** level for level in range(self.num_levels)]
        self.num_server_per_job = num_server_per_job
        self.num_server_per_group = self.num_servers // self.num_groups
        self.num_group_per_job = self.num_server_per_job // self.num_server_per_group
        self.num_repetitions = num_repetitions
        self.num_steps = self.num_levels + 1
        assert(self.num_server_per_group == r)
        assert(self.num_server_per_job <= self.num_servers and self.num_servers % self.num_server_per_job == 0) # make sure we have an integer number of jobs
        assert(self.num_server_per_job % self.num_server_per_group == 0)
        self.name = "sipco_allreduce"
    
    def plan_arrivals(self, total_message_size, start_time=0):
        message_size = math.ceil(total_message_size / (self.num_levels * self.num_server_per_group))
        traffic_arrival_events = []
        start_time = start_time
    
        for step in range(self.num_steps):
            self.gpu_groups = [list(range(group_id*self.num_server_per_group, (group_id+1)*self.num_server_per_group)) for group_id in range(self.num_group_per_job)]
            for level in range(0, self.num_levels):
                intergroup_communication_nodes = []
                num_iteration = self.num_group_per_job // self.num_switches_in_level[level]
                if num_iteration > 0: num_groups_per_iteration = len(self.gpu_groups) // num_iteration
                for it in range(num_iteration):
                    group_list = [group for group in self.gpu_groups[it*num_groups_per_iteration:(it+1)*num_groups_per_iteration]]
                    group_list = self.findCommunicatingNodes(group_list)
                    intergroup_communication_nodes += group_list
                self.gpu_groups = [list(itertools.chain.from_iterable(self.gpu_groups[it*num_groups_per_iteration:(it+1)*num_groups_per_iteration])) for it in range(num_iteration)]
                for communication_nodes in intergroup_communication_nodes:
                    for i in range(len(communication_nodes)):
                        for j in range(len(communication_nodes)):
                            if i != j:
                                src, dst = communication_nodes[i], communication_nodes[j]
                                traffic_arrival_events.append( (start_time+step, src, dst, int(message_size)) )
        return traffic_arrival_events
    
    def findCommunicatingNodes(self, group_list):
        if len(group_list) == 1: return group_list
        num_gpus_per_group = len(group_list[0])
        communicating_nodes = [[group[i] for group in group_list] for i in range(num_gpus_per_group)]
        return communicating_nodes
