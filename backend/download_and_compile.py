import osmnx as ox
import pickle
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# The target city (OSMnx will geocode this and draw a boundary box)
PLACE_NAME = "Bengaluru, Karnataka, India"

# Define where you want the files to land (matches your config.py defaults)
DATA_DIR = "data"
BINARY_PICKLE_PATH = f"{DATA_DIR}/bengaluru_network.pkl"
GRAPHML_BACKUP_PATH = f"{DATA_DIR}/bengaluru_network.graphml"

def download_and_compile_graph():
    logger.info("==================================================")
    logger.info(f"🚀 STARTING LIVE DOWNLOAD: {PLACE_NAME}")
    logger.info("==================================================")
    
    # Create the data directory if it doesn't exist so we don't get a FileNotFoundError
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        logger.info(f"Step 1: Downloading live 'drive' network from OpenStreetMap...")
        logger.info("⏳ Please be patient! Downloading a massive city takes 2-5 minutes...")
        
        # This is the magic line that fetches the live road data. 
        # network_type="drive" ensures we only get roads cars can actually drive on.
        G = ox.graph_from_place(PLACE_NAME, network_type="drive", simplify=True)
        
        node_count = len(G.nodes)
        edge_count = len(G.edges)
        logger.info(f"✅ Download complete! (Nodes: {node_count}, Edges: {edge_count})")
        
        logger.info("Step 2: Saving a .graphml backup just in case...")
        ox.save_graphml(G, GRAPHML_BACKUP_PATH)
        
        logger.info("Step 3: Compiling directly to binary (.pkl)...")
        # HIGHEST_PROTOCOL creates the fastest and smallest binary file
        with open(BINARY_PICKLE_PATH, 'wb') as f:
            pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
            
        file_size_mb = os.path.getsize(BINARY_PICKLE_PATH) / (1024 * 1024)
        logger.info(f"✅ Success! Binary graph generated ({file_size_mb:.2f} MB).")
        logger.info("Your routing engine is ready to go.")
        
    except Exception as e:
        logger.error(f"❌ Failed to download or compile graph: {e}")
        logger.error("If it timed out, OSM servers might be under heavy load. Try again in a minute.")

if __name__ == "__main__":
    download_and_compile_graph()