from .synthetic_traffic_generator import *

'''
Generates primitive all-to-one traffic.
'''
class PrimitiveAllToOneTrafficGenerator(SyntheticTrafficGenerator):
    def __init__(self, p, dst_node, num_repetitions=1):
        SyntheticTrafficGenerator.__init__(self, p)
        self.num_servers = p
        self.dst_node = dst_node
        self.num_repetitions = num_repetitions
        self.name = "primitive_alltoone" # same as incast
    
    def plan_arrivals(self, total_message_size, start_time=0):
        traffic_arrival_events = []
        for _ in range(self.num_repetitions):
            for src in range(self.num_servers):
                if src != self.dst_node:
                    traffic_arrival_events.append((start_time, src, self.dst_node, int(total_message_size)))
            start_time += 1
        return traffic_arrival_events