import numpy as np
from collections import defaultdict
from network_topology.network_topology import NetworkTopology

def CartProduct(set1, set2):
    cart_prod = []
    for element1 in set1:
        for element2 in set2:
            cart_prod.append(element1 + element2)
    return cart_prod

def NormalizeSquareMatrix(matrix, norm):
    num_entries = len(matrix)
    new_matrix = [0] * num_entries
    total = sum([sum(x) for x in matrix])
    multiplicity = float(norm) / total
    for i in range(num_entries):
        new_matrix[i] = [0.] * num_entries
        for j in range(num_entries):
            new_matrix[i][j] = float(matrix[i][j]) * multiplicity
    return new_matrix

class NDTorusNetworkTopology(NetworkTopology):
    def __init__(self, numSwitchesInDimension, link_bw):
        NetworkTopology.__init__(self)
        self.numDimensions = len(numSwitchesInDimension)
        self.numSwitchesInDimension = list(numSwitchesInDimension)
        assert(self.numDimensions == len(self.numSwitchesInDimension))
        self.total_num_nodes = np.prod(numSwitchesInDimension)
        self.name = "{}D_torus".format(len(numSwitchesInDimension))
        self.dimension_str = "_".join([str(x) for x in numSwitchesInDimension])
        self.link_bw = link_bw
        ## Step 1: generate the switches
        self.CoordToIndex = {}
        self.IndexToCoord = {}
        self.adjacencyList = {}
        return
    
    def getNumServers(self):
        return self.total_num_nodes
    
    def getNumSwitches(self):
        return 0
    
    def getNumTransceivers(self):
        return self.total_num_nodes * self.numDimensions * 2

    def getName(self):
        network_name = self.name + "_" + self.dimension_str + "_{}nodes".format(self.total_num_nodes)
        return network_name

    def getTopologyName(self):
        return "{}D Torus".format(len(self.numSwitchesInDimension))
    
    def getLinkBW(self):
        return self.link_bw
    
    # Creates all the switches in the network
    def createSwitches(self):
        allCoords = [[x, ] for x in range(self.numSwitchesInDimension[0])]
        for dim in range(1, self.numDimensions, 1):
            currDimensionIndices = [[x] for x in range(self.numSwitchesInDimension[dim])]
            allCoords = CartProduct(allCoords, currDimensionIndices)
        index = 0
        for coord in allCoords:
            self.CoordToIndex[tuple(coord)] = index
            self.IndexToCoord[index] = tuple(coord)
            index += 1
        return

    # in this case, we first don't connect the final dimension
    def wireNetwork(self):
        print("[Setup] Wiring nd torus network.")
        self.createSwitches()
        for coord in self.CoordToIndex.keys():
            toConnectCoordinates = []
            for dim in range(self.numDimensions):
                ind = coord[dim]
                neighbor1DimIndex = ind - 1
                neighbor2DimIndex = ind + 1
                if ind == 0:
                    neighbor1DimIndex = self.numSwitchesInDimension[dim] - 1
                elif ind == self.numSwitchesInDimension[dim] - 1:
                    neighbor2DimIndex = 0
                mutableCoordListNeighbor1 = list(coord)
                mutableCoordListNeighbor1[dim] = neighbor1DimIndex
                mutableCoordListNeighbor2 = list(coord)
                mutableCoordListNeighbor2[dim] = neighbor2DimIndex
                neighbor1Coord = tuple(mutableCoordListNeighbor1)
                neighbor2Coord = tuple(mutableCoordListNeighbor2)
                toConnectCoordinates.append(neighbor1Coord)
                toConnectCoordinates.append(neighbor2Coord)
            currIndex = self.CoordToIndex[coord]
            self.adjacencyList[currIndex] = []
            for neighborCoord in toConnectCoordinates:
                neighborIndex = self.CoordToIndex[neighborCoord]
                self.adjacencyList[currIndex].append(neighborIndex)
        assert(len(self.adjacencyList) == self.total_num_nodes)
        assert(self.CheckTopologicalSymmetry())
        self.standardizeAdjacencyList()
        return

    def standardizeAdjacencyList(self):
        self.adjacency_list = {}
        for src in self.adjacencyList.keys():
            self.adjacency_list[src] = defaultdict(int)
            for dst in self.adjacencyList[src]:
                self.adjacency_list[src][dst] += 1

    # checks and see if the network topology is symmetrical (i.e if all links are bidirectional)
    def CheckTopologicalSymmetry(self):
        for switchIndex in self.adjacencyList.keys():
            for neighborIndex in self.adjacencyList[switchIndex]:
                if switchIndex not in self.adjacencyList[neighborIndex]:
                    return False
        return True

    ## writes the adjacency matrix into a netbench .topology file format
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
        num_nodes = len(self.adjacency_list)
        assert(self.total_num_nodes == num_nodes)
        prefix += ("|V|={}".format(num_nodes) + "\n")
        prefix += ("|E|={}".format(num_edges) + "\n")
        prefix += ("Switches=set()\n\n")
        prefix += "ToRs=incl_range({},{})\n".format(0, num_nodes-1)
        prefix += "Servers=incl_range({},{})\n\n".format(0, num_nodes-1)
        return prefix + topol_str
    
    def generateTrafficEventsString(self, trace_events_list):
        str_builder = ""
        virtual_servers_offset = 0
        number_of_flows = 0
        for (timestamp, src, dst, sum_bytes) in trace_events_list:
            src_virtual = virtual_servers_offset + src
            dst_virtual = virtual_servers_offset + dst
            assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list), "{},{}".format(src_virtual,dst_virtual)
            if src_virtual != dst_virtual:
                str_builder += "{},{},{},{}\n".format(timestamp, int(src_virtual), int(dst_virtual), sum_bytes)
                number_of_flows += 1
        return str_builder, number_of_flows
    
    def WriteNetBenchToRTrafficProbabilityFile(self, filename, traffic_matrix_tor_to_tor):
        numToRs = len(self.adjacencyList.keys())
        offset = numToRs
        pair = 0
        normed_tm = NormalizeSquareMatrix(traffic_matrix_tor_to_tor, 1.)
        str_builder = "#tor_pair_id,src,dst,pdf_num_bytes\n"
        for i in range(numToRs):
            for j in range(numToRs):
                if i != j and normed_tm[i][j] > 0.:
                    str_builder += ("{},{},{},{}".format(pair, i + offset, j + offset, "{:.6E}".format(normed_tm[i][j])) + "\n")
                    pair += 1
        str_builder += "\n"
        with open(filename, 'w+') as f:
            f.write(str_builder)
        return

