import math
from .synthetic_traffic_generator import *

'''
Generates hierarchical allreduce traffic..
'''
class HierarchicalAllReduceTrafficGenerator(SyntheticTrafficGenerator): 
    # Hierarchical ring-allreduce
    def __init__(self, p, k, num_server_per_job):
        SyntheticTrafficGenerator.__init__(self, p=p) # 100 packets per flow
        self.num_servers = p
        self.num_groups = k
        self.num_server_per_job = num_server_per_job
        self.num_server_per_group = self.num_servers // self.num_groups
        self.num_repetitions_intragroup = int(2 * (p//k - 1))
        self.num_repetitions_intergroup = int(2 * (k - 1))
        assert(self.num_servers % self.num_server_per_job == 0) # make sure we have an integer number of jobs
        self.num_jobs = self.num_servers // self.num_server_per_job
        self.name = "hierarchical_allreduce"

    def plan_arrivals(self, total_message_size, start_time=0):
        per_node_message_size = math.ceil(total_message_size / self.num_server_per_group)
        traffic_arrival_events = []
        start_time = start_time
        for _ in range(self.num_repetitions_intragroup):
            # Step 1): first intragroup ring-allreduce parallelized for all the groups
            for group_id in range(self.num_groups):
                group_offset = group_id * self.num_server_per_group
                for src in range(group_offset, group_offset  + self.num_server_per_group):
                    dst = group_offset + (src + 1 - group_offset) % self.num_server_per_group
                    if src != dst: traffic_arrival_events.append( (start_time, src, dst, int(per_node_message_size)) )
            start_time += 1
        
        for _ in range(self.num_repetitions_intergroup):
            # Step 2): then intergroup ring-allreduce
            # first select a leader node from each group (for now assume it to be the first node within each group)
            for group_id in range(self.num_groups):
                src = group_id * self.num_server_per_group
                dst = (group_id + 1) % self.num_groups * self.num_server_per_group
                if src != dst: traffic_arrival_events.append( (start_time, src, dst, int(per_node_message_size)) )
            start_time += 1
        
        for _ in range(self.num_repetitions_intragroup):    
            # Step 3): then finish with intragroup ring-allreduce
            for group_id in range(self.num_groups):
                group_offset = group_id * self.num_server_per_group
                for src in range(group_offset, group_offset  + self.num_server_per_group):
                    dst = group_offset + (src + 1 - group_offset) % self.num_server_per_group
                    if src != dst: traffic_arrival_events.append( (start_time, src, dst, int(per_node_message_size)) )
            start_time += 1
        return traffic_arrival_events