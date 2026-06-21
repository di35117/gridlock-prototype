import osmnx as ox
import pickle
import os

# Define the target location and the output path
place_name = "Bengaluru, Karnataka, India"
output_path = "backend/data/bengaluru_road_graph.pkl"

# Ensure the backend/data directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

print(f"1. Contacting OpenStreetMap to download the live road network for {place_name}...")
print("   (This might take 3 to 5 minutes depending on your internet connection. Do not close the terminal!)")

# Download the driveable road network directly into an OSMnx graph (which keeps Shapely geometries safe)
G = ox.graph_from_place(place_name, network_type='drive')

print("2. Download successful! Compressing directly into binary Pickle format...")

# Save it directly as our lightweight .pkl file
with open(output_path, "wb") as f:
    pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

print(f"3. SUCCESS! Your completely fixed, geometry-aware binary file is saved at: {output_path}")
print("   You are ready to deploy!")