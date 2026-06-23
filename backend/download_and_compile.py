import osmnx as ox
import networkx as nx
import pickle
import os
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
PLACE_NAME = "Bengaluru, Karnataka, India"
DATA_DIR = "data"
PKL_FILENAME = "bengaluru_network.pkl"

def compile_bengaluru_graph():
    """
    Downloads the Bengaluru road network and saves it DIRECTLY to a binary .pkl file,
    skipping the bulky .graphml intermediate file to save disk space and Git bandwidth.
    """
    logger.info(f"Starting direct-to-binary compilation for: {PLACE_NAME}")
    start_time = time.time()

    # 1. Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    pkl_path = os.path.join(DATA_DIR, PKL_FILENAME)

    # 2. Download the graph directly into RAM
    logger.info("Downloading road network from OpenStreetMap (this may take 2-3 minutes)...")
    try:
        # network_type="drive" ensures we only get roads cars can drive on
        G = ox.graph_from_place(PLACE_NAME, network_type="drive", simplify=True)
        logger.info(f"Download complete. Graph contains {len(G.nodes)} nodes and {len(G.edges)} edges.")
    except Exception as e:
        logger.error(f"Failed to download graph from OSM: {e}")
        return

    # 3. Add travel times to the edges (crucial for shortest-path routing)
    logger.info("Imputing speeds and calculating edge travel times...")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    # 4. Save directly to the binary pickle format (Skip GraphML entirely)
    logger.info(f"Serializing graph directly to {pkl_path}...")
    try:
        with open(pkl_path, "wb") as f:
            pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        file_size_mb = os.path.getsize(pkl_path) / (1024 * 1024)
        logger.info(f"Success! Binary graph saved. File size: {file_size_mb:.2f} MB")
        logger.info(f"Total compilation time: {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Failed to save binary graph: {e}")

if __name__ == "__main__":
    compile_bengaluru_graph()