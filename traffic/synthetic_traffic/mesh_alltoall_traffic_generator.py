import math
from .synthetic_traffic_generator import *

'''
Generates mesh alltoall traffic.
'''
class MeshAllToAllTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, p, num_server_per_job=32):
        SyntheticTrafficGenerator.__init__(self, p=p) # 100 packets per flow
        self.num_servers = p
        self.num_server_per_job = num_server_per_job
        self.num_repetitions = 1
        assert(self.num_servers % self.num_server_per_job == 0) # make sure we have an integer number of jobs
        self.num_jobs = self.num_servers // self.num_server_per_job
        self.name = "mesh_alltoall"
    
    def plan_arrivals(self, total_message_size, start_time=0):
        # same communication pattern as mesh all-reduce but with only one round of transfer: diffuse
        # assume the total message size to be the sum of all messages it needs to send to other nodes
        per_node_message_size = math.ceil(total_message_size / self.num_nodes)
        traffic_arrival_events = []
        start_time = start_time
        for it in range(self.num_repetitions):
            start_time = start_time + it
            for src in range(self.num_servers):
                for dst in range(self.num_servers):
                    if src != dst:
                        traffic_arrival_events.append( (start_time, src, dst, int(per_node_message_size)) )
        return traffic_arrival_events