from .synthetic_traffic_generator import *

'''
Generates primitive one-to-all traffic.
'''
class PrimitiveOneToAllTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, p, src_node=0, num_repetitions=1):
        SyntheticTrafficGenerator.__init__(self, p)
        self.num_servers = p
        self.src_node = src_node
        self.num_repetitions = num_repetitions
        self.name = "primitive_onetoall"
    
    def plan_arrivals(self, total_message_size, start_time=0):
        traffic_arrival_events = []
        for i in range(self.num_repetitions):
            for dst in range(self.num_servers):
                if self.src_node != dst:
                    traffic_arrival_events.append((start_time, self.src_node, dst, int(total_message_size)))
            start_time += 1
        return traffic_arrival_events