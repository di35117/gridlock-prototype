import logging
import networkx as nx
import osmnx as ox
from sqlalchemy import text
from database import engine
from config import BENGALURU_GRAPH_CACHE

logger = logging.getLogger(__name__)

_GRAPH_CACHE = None

def _get_graph():
    global _GRAPH_CACHE
    if _GRAPH_CACHE is None:
        logger.info(f"Loading road graph from {BENGALURU_GRAPH_CACHE}...")
        try:
            _GRAPH_CACHE = ox.load_graphml(BENGALURU_GRAPH_CACHE)
            logger.info("Graph loaded successfully into memory.")
        except Exception as e:
            logger.error(f"Failed to load graphml file: {e}")
            raise RuntimeError("Graph file not found.")
    return _GRAPH_CACHE

async def _get_construction_coordinates(corridor: str) -> list[tuple[float, float]]:
    query = text("""
        SELECT latitude, longitude FROM incidents 
        WHERE corridor ILIKE :corridor AND event_cause = 'construction'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        rows = result.fetchall()
    return [(float(row.latitude), float(row.longitude)) for row in rows]

async def calculate_tactical_diversion(corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    logger.info(f"Calculating tactical diversion for {corridor}...")
    G = _get_graph()
    
    orig_node = ox.distance.nearest_nodes(G, X=o_lon, Y=o_lat)
    dest_node = ox.distance.nearest_nodes(G, X=d_lon, Y=d_lat)
    
    construction_coords = await _get_construction_coordinates(corridor)
    blocked_nodes = []
    if construction_coords:
        lons = [c[1] for c in construction_coords]
        lats = [c[0] for c in construction_coords]
        blocked_nodes = ox.distance.nearest_nodes(G, X=lons, Y=lats)
        if not isinstance(blocked_nodes, list):
            blocked_nodes = [blocked_nodes]
        blocked_nodes = list(set(blocked_nodes))

    G_safe = G.copy()
    G_safe.remove_nodes_from(blocked_nodes)
    
    try:
        route = nx.shortest_path(G_safe, orig_node, dest_node, weight='length')
        status = "Optimal Diversion Found"
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        logger.warning("No safe path exists avoiding all construction. Falling back to shortest path.")
        route = nx.shortest_path(G, orig_node, dest_node, weight='length')
        status = "Warning: Forced Path (Construction Unavoidable)"

    geojson_coords = [[G.nodes[node]['x'], G.nodes[node]['y']] for node in route]
    route_geojson = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": geojson_coords},
        "properties": {"corridor": corridor}
    }
    
    # BARRICADE FIX: Capture upstream nodes on directed graphs
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