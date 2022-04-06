import os
import matplotlib.pyplot as plt

class SyntheticTrafficGenerator(object):
    def __init__(self, p):
        self.num_nodes = p 
        self.name = ""

    # Generate the traffic probability matrix based on traffic arrival events
    def generateProbabilityMatrix(self, traffic_arrival_events, num_nodes):
        traffic_matrix = [[0]*num_nodes for _ in range(num_nodes)]
        for _, src, dst, byte in traffic_arrival_events:
            assert(src in range(len(traffic_matrix)) and dst in range(len(traffic_matrix)))
            traffic_matrix[src][dst] += byte
        return traffic_matrix

    # Normalize the sum of all entries in a squre matrix to 'norm'
    def NormalizeSquareMatrix(self, matrix, norm):
        num_entries = len(matrix)
        new_matrix = [0] * num_entries
        total = sum([sum(x) for x in matrix])
        multiplicity = float(norm) / total
        for i in range(num_entries):
            new_matrix[i] = [0.] * num_entries
            for j in range(num_entries):
                new_matrix[i][j] = float(matrix[i][j]) * multiplicity
        return new_matrix

    def get_name(self):
        return self.name

    def plan_arrivals(self):
        raise Exception("Plan Arrivals method is not implemented.")

    # Plot traffic heatmap to "file_path"
    def drawHeatmap(self, probability_matrix, file_path=None):
        print("*** Drawing heat map...")
        probability_matrix = self.NormalizeSquareMatrix(probability_matrix, 1)
        plt.matshow(probability_matrix, cmap="Reds", aspect='auto')
        plt.colorbar()
        if file_path and not os.path.isfile(file_path): plt.savefig(file_path, dpi=300)