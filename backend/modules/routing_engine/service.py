import logging
import asyncio
import networkx as nx
import osmnx as ox
from sqlalchemy import text
from database import engine

# Import the cache path directly from config
from config import BENGALURU_GRAPH_CACHE

logger = logging.getLogger(__name__)

# Global cache so we only load the 50MB graph file once
_GRAPH_CACHE = None

def _get_graph():
    global _GRAPH_CACHE
    if _GRAPH_CACHE is None:
        logger.info(f"Loading road graph from {BENGALURU_GRAPH_CACHE}. This will take ~10 seconds on the first request...")
        try:
            # Load graph and project to standard lat/lon
            _GRAPH_CACHE = ox.load_graphml(BENGALURU_GRAPH_CACHE)
            logger.info("Graph loaded successfully into memory.")
        except Exception as e:
            logger.error(f"Failed to load graphml file: {e}")
            raise RuntimeError("Graph file not found. Ensure the download_graph script was run.")
    return _GRAPH_CACHE

async def _get_construction_coordinates(corridor: str) -> list[tuple[float, float]]:
    """Fetch exact lat/lons of active construction on this corridor from the database."""
    query = text("""
        SELECT latitude, longitude FROM incidents 
        WHERE corridor ILIKE :corridor AND event_cause = 'construction'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        rows = result.fetchall()
        
    return [(float(row.latitude), float(row.longitude)) for row in rows]

def _run_heavy_graph_math(G, corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float, construction_coords: list) -> dict:
    """Synchronous function to handle all CPU-bound NetworkX and OSMnx operations."""
    
    # 2. Get origin and destination nodes nearest to the provided coordinates
    orig_node = ox.distance.nearest_nodes(G, X=o_lon, Y=o_lat)
    dest_node = ox.distance.nearest_nodes(G, X=d_lon, Y=d_lat)
    
    # 3. Find nearest graph nodes for construction zones
    blocked_nodes = []
    if construction_coords:
        lons = [c[1] for c in construction_coords]
        lats = [c[0] for c in construction_coords]
        blocked_nodes = ox.distance.nearest_nodes(G, X=lons, Y=lats)
        
        if not isinstance(blocked_nodes, list):
            blocked_nodes = [blocked_nodes]
        blocked_nodes = list(set(blocked_nodes))

    # 4. Create a safe graph by removing the blocked nodes
    G_safe = G.copy()
    G_safe.remove_nodes_from(blocked_nodes)
    
    # 5. Calculate the shortest path on the safe graph
    try:
        route = nx.shortest_path(G_safe, orig_node, dest_node, weight='length')
        status = "Optimal Diversion Found"
    except (nx.NetworkXNoPath, nx.NodeNotFound): 
        logger.warning("No safe path exists avoiding all construction. Falling back to shortest path.")
        route = nx.shortest_path(G, orig_node, dest_node, weight='length')
        status = "Warning: Forced Path (Construction Unavoidable)"

    # 6. Format the route as a GeoJSON LineString for the React frontend
    geojson_coords = []
    for node in route:
        geojson_coords.append([G.nodes[node]['x'], G.nodes[node]['y']])
        
    route_geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": geojson_coords
        },
        "properties": {"corridor": corridor}
    }
    
    # 7. Identify Barricade Points (Nodes immediately preceding the blocked zones)
    barricade_points = []
    blocked_set = set(blocked_nodes)
    
    for blocked in blocked_nodes:
        for neighbor in nx.all_neighbors(G, blocked):
            if neighbor not in blocked_set:
                barricade_points.append({
                    "lat": G.nodes[neighbor]['y'],
                    "lon": G.nodes[neighbor]['x']
                })
                
    unique_barricades = list({(b["lat"], b["lon"]): b for b in barricade_points}.values())

    return {
        "status": status,
        "route_geojson": route_geojson,
        "barricade_points": unique_barricades[:15], 
        "blocked_construction_nodes": len(blocked_nodes)
    }

async def calculate_tactical_diversion(corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    logger.info(f"Calculating tactical diversion for {corridor}...")
    G = await asyncio.to_thread(_get_graph)
    construction_coords = await _get_construction_coordinates(corridor)
    result = await asyncio.to_thread(
        _run_heavy_graph_math, G, corridor, o_lat, o_lon, d_lat, d_lon, construction_coords
    )
    return result

async def generate_network_metrics_geojson() -> dict:
    """
    Converts the OSMNX Graph into a GeoJSON FeatureCollection.
    Merges real-time ML risk scores from the database into the road properties.
    """
    logger.info("Generating network metrics GeoJSON...")
    
    # 1. Load the graph safely in a background thread if it's the first time
    G = await asyncio.to_thread(_get_graph)
    
    # 2. Fetch the real-time ML risk scores from the database
    query = text("SELECT corridor, risk_score FROM corridor_risk_profiles")
    corridor_risks = {}
    async with engine.connect() as conn:
        result = await conn.execute(query)
        for row in result.fetchall():
            if row.corridor:
                normalized_name = str(row.corridor).strip().lower()
                corridor_risks[normalized_name] = float(row.risk_score or 0.0)

    # 3. Offload the heavy loop to the background thread to prevent blocking
    def _build_features(graph, risks):
        features = []
        for u, v, data in graph.edges(data=True):
            if 'geometry' in data:
                coords = list(data['geometry'].coords)
            else:
                coords = [(graph.nodes[u]['x'], graph.nodes[u]['y']),
                          (graph.nodes[v]['x'], graph.nodes[v]['y'])]
                
            name = data.get('name', 'Unknown')
            if isinstance(name, list):
                name = name[0]
                
            normalized_name = str(name).strip().lower()
            risk_score = risks.get(normalized_name, 0.0)
            
            highway_type = data.get('highway', '')
            if isinstance(highway_type, list):
                highway_type = highway_type[0]
                
            if highway_type in ['primary', 'secondary', 'trunk', 'motorway', 'primary_link', 'secondary_link']:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {"name": name, "highway": highway_type, "risk_score": risk_score}
                })
        return features

    features = await asyncio.to_thread(_build_features, G, corridor_risks)
    logger.info(f"Generated {len(features)} road segments for MapLibre rendering.")
    
    return {
        "type": "FeatureCollection",
        "features": features
    }