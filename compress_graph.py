import networkx as nx
import pickle

# Update this path if your data folder is somewhere else locally!
input_path = "backend/data/bengaluru_road_graph.graphml"
output_path = "backend/data/bengaluru_road_graph.pkl"

print("1. Loading heavy GraphML XML into local laptop RAM...")
G = nx.read_graphml(input_path)

print("2. Serializing into lightweight binary Pickle...")
with open(output_path, "wb") as f:
    pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

print("3. Done! You can now safely delete the massive .graphml file.")