from .synthetic_traffic_generator import *

'''
Generates ring allgather traffic.
'''
class RingAllGatherTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, p, num_server_per_job):
        SyntheticTrafficGenerator.__init__(self, p=p)
        self.num_servers = p
        self.num_server_per_job = num_server_per_job
        self.num_repetitions = (self.num_servers - 1)
        assert(self.num_servers % self.num_server_per_job == 0) # make sure we have an integer number of jobs
        self.name = "ring_allgather"

    def plan_arrivals(self, total_message_size, start_time=0):
        per_node_message_size = total_message_size
        traffic_arrival_events = []
        start_time = start_time
        for iteration in range(self.num_repetitions):
            for job_id in range(self.num_servers//self.num_server_per_job):
                offset = job_id * self.num_server_per_job
                for i in range(self.num_server_per_job-1):
                    src, dst = offset + i, offset + i + 1
                    traffic_arrival_events.append( (iteration+start_time, src, dst, int(per_node_message_size)) )
                traffic_arrival_events.append( (iteration+start_time, offset+self.num_server_per_job-1, offset, int(per_node_message_size)) )
        return traffic_arrival_events