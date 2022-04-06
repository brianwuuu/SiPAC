import sys

class NetworkTopology(object):
    def __init__(self):
        self.adjacency_list = {}

    # An abstract function called by external user to wire the network together.
    def wireNetwork(self):
        raise Exception("Wiring method is not implemented.")

    # Retrieves the number of servers (CUs in this case) that this topology instance supports.
    def getNumServers(self):
        raise Exception("Server number query method is not implemented.")

    # Retrieves the number of switches in this topology.
    def getNumServers(self):
        raise Exception("Switch number query method is not implemented.")

    def generateLinkDelayFileString(self):
        # should be overwritten by child class if child class wishes to provide different link delays/bandwidths for topology
        return ""
    
    def getName(self):
        raise Exception("Child classes must override this method.")

    def getLinkBW(self):
        raise Exception("Child classes must override this method.")
    
    def getNumLinks(self):
        # return number of bidirectional links
        link_count = 0
        for src in self.adjacency_list.keys():
            for dst in self.adjacency_list[src]:
                link_count += self.adjacency_list[src][dst]
        return link_count // 2 # bidirectional
    
    def getNumTransceivers(self):
        # if not specified otherwise, the number of transceivers = num bidirectional links * 2
        # if needed, implement in child class to inherit
        return self.getNumLinks() * 2

    def checkNetworkConnectivity(self):
        # make sure the network is fully connected
        stack = [list(self.adjacency_list.keys())[0]]
        nodes = set()
        while stack:
            node = stack.pop(0)
            for neighbor in self.adjacency_list[node].keys(): 
                if neighbor not in nodes:
                    stack.append(neighbor)
                nodes.add(neighbor)
        assert(len(nodes) == len(set(self.adjacency_list.keys())))
        assert(nodes == set(self.adjacency_list.keys()))