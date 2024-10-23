import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from qibo.symbols import Z
from qibo import hamiltonians, set_backend

set_backend("numpy")

# Create a graph based on the specified topology
G = nx.Graph()

# Define edges based on the user's topology
edges = [
    # (0, 1), (0, 2), (0, 3), (0, 6), (0, 8), (0, 10), (0, 11), (0, 12),
    (1, 2), (1, 4), (1, 7), (1, 9), (1, 10),
    (2, 3), (2, 4),
    # (3, 4),
    # (4, 5), (4, 7),
    # (5, 6), (5, 7),
    # (6, 8), (6, 7),
    # (7, 8), (7, 9),
    # (8, 9), (8, 10),
    # (9, 10),
    # (10, 11),
    # (11, 12)
]

G.add_edges_from(edges)

# Draw the graph to visualize its topology
pos = nx.spring_layout(G)  
nx.draw(G, pos, with_labels=True, node_color='lightblue', font_weight='bold', node_size=700, font_size=10)
plt.title("Graph Topology")
plt.savefig("./figures/topology.png")

nedges = len(G.edges)

# TODO: this is random now but has to encode the traffic data
params = np.random.uniform(0, 1, nedges)

symbolic_ham = sum((params[i] * Z(edge[0]) * Z(edge[1])) for i, edge in enumerate(G.edges))
ham = hamiltonians.SymbolicHamiltonian(symbolic_ham)


