from .synthetic_traffic_generator import *

'''
Generates primitive all-to-all traffic.
'''
class PrimitiveAllToAllTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, p, num_repetitions=1):
        SyntheticTrafficGenerator.__init__(self, p)
        self.num_servers = p
        self.num_repetitions = num_repetitions
        self.name = "primitive_alltoall"
    
    def plan_arrivals(self, total_message_size, start_time=0):
        traffic_arrival_events = []
        for _ in range(self.num_repetitions):
            for src in range(self.num_servers):
                for dst in range(self.num_servers):
                    if src != dst:
                        traffic_arrival_events.append((start_time, src, dst, int(total_message_size)))
            start_time += 1
        return traffic_arrival_events