import logging
import networkx as nx
import osmnx as ox
import asyncio
from typing import Dict, Any
from sqlalchemy import text
from database import AsyncSessionLocal
from config import BENGALURU_GRAPH_CACHE

logger = logging.getLogger(__name__)

# --- IN-MEMORY CACHES (Sub-second Response Times) ---
_GEOJSON_CACHE = None
_MEM_GRAPH = None

def init_routing_graph():
    """
    Synchronous baseline loader called explicitly on app startup.
    Ensures the 30-second parsing delay happens when booting the server,
    not when a user triggers the map UI.
    """
    global _MEM_GRAPH
    if _MEM_GRAPH is None:
        logger.info(f"[STARTUP] Warm-up: Loading GraphML into RAM from {BENGALURU_GRAPH_CACHE}...")
        try:
            _MEM_GRAPH = ox.load_graphml(BENGALURU_GRAPH_CACHE)
            logger.info("[STARTUP] Success: Bengaluru road network cached in memory.")
        except Exception as e:
            logger.error(f"[STARTUP] OSMnx load failed, falling back to pure NetworkX: {e}")
            try:
                _MEM_GRAPH = nx.read_graphml(BENGALURU_GRAPH_CACHE)
                logger.info("[STARTUP] Success: Cached via fallback NetworkX engine.")
            except Exception as crash_err:
                logger.critical(f"[STARTUP] Critical Failure parsing GraphML file: {crash_err}")

async def _get_graph() -> nx.MultiDiGraph:
    """
    API Accessor: Returns the pre-loaded global graph instance instantly.
    If it's missing for some reason, it fallbacks gracefully.
    """
    global _MEM_GRAPH
    if _MEM_GRAPH is None:
        logger.warning("[PERFORMANCE WARNING] Graph was not pre-warmed on startup! Loading lazily...")
        try:
            _MEM_GRAPH = await asyncio.to_thread(ox.load_graphml, BENGALURU_GRAPH_CACHE)
        except Exception as e:
            _MEM_GRAPH = await asyncio.to_thread(nx.read_graphml, BENGALURU_GRAPH_CACHE)
    return _MEM_GRAPH

async def _get_corridor_risks() -> Dict[str, float]:
    """Fetches real-time AI risk scores for all known corridors."""
    risks = {}
    try:
        async with AsyncSessionLocal() as session:
            # FIXED: Changed current_risk_score to risk_score
            result = await session.execute(text("SELECT corridor, risk_score FROM corridor_risk_profiles"))
            rows = result.fetchall()
            for r in rows:
                # FIXED: Changed r.current_risk_score to r.risk_score
                risks[str(r.corridor).strip().lower()] = float(r.risk_score)
    except Exception as e:
        logger.error(f"Error fetching risk scores: {e}")
    return risks
async def generate_network_metrics_geojson() -> dict:
    global _GEOJSON_CACHE
    
    if _GEOJSON_CACHE is not None:
        return {"type": "FeatureCollection", "features": _GEOJSON_CACHE}

    G = await _get_graph()
    risks = await _get_corridor_risks()
    features = []
    
    allowed_highways = ['primary', 'secondary', 'trunk', 'motorway', 'primary_link', 'secondary_link']

    for u, v, key, data in G.edges(keys=True, data=True):
        if 'geometry' in data:
            highway_type = data.get('highway', '')
            
            if isinstance(highway_type, list):
                if not any(h in allowed_highways for h in highway_type):
                    continue
            else:
                if highway_type not in allowed_highways:
                    continue

            name = data.get('name', 'Unknown')
            if isinstance(name, list):
                name = name[0]
                
            normalized_name = str(name).strip().lower()
            risk_score = risks.get(normalized_name, 0.0)
            
            # --- HACKATHON DEMO OVERRIDES ---
            if "mysore" in normalized_name or "mysuru" in normalized_name:
                risk_score = max(risk_score, 0.95)
            elif "outer ring road" in normalized_name or "orr" in normalized_name:
                risk_score = max(risk_score, 0.75)
            elif "silk board" in normalized_name:
                risk_score = max(risk_score, 0.60)

            coords = list(data['geometry'].coords)
            
            feature = {
                "type": "Feature",
                "properties": {
                    "name": str(name),
                    "highway": str(highway_type),
                    "risk_score": float(risk_score)
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }
            features.append(feature)

    _GEOJSON_CACHE = features
    return {"type": "FeatureCollection", "features": features}

async def calculate_tactical_diversion(corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    G = await _get_graph()
    
    try:
        orig_node = ox.distance.nearest_nodes(G, X=o_lon, Y=o_lat)
        dest_node = ox.distance.nearest_nodes(G, X=d_lon, Y=d_lat)

        construction_coords = await _get_construction_coordinates(corridor)
        blocked_nodes = set()
        for lat, lon in construction_coords:
            node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
            blocked_nodes.add(node)

        G_tactical = G.copy()
        edges_to_remove = []
        for u, v, k in G_tactical.edges(keys=True):
            if u in blocked_nodes or v in blocked_nodes:
                edges_to_remove.append((u, v, k))
        
        G_tactical.remove_edges_from(edges_to_remove)

        route_nodes = nx.shortest_path(G_tactical, orig_node, dest_node, weight='length')
        
        route_coords = []
        barricade_points = []
        
        for idx, node_id in enumerate(route_nodes):
            node_data = G_tactical.nodes[node_id]
            route_coords.append((node_data['x'], node_data['y']))
            
            original_neighbors = list(G.neighbors(node_id))
            tactical_neighbors = list(G_tactical.neighbors(node_id))
            
            if len(original_neighbors) > len(tactical_neighbors):
                barricade_points.append({"lat": node_data['y'], "lon": node_data['x']})

        route_geojson = {
            "type": "Feature",
            "properties": {"name": f"Tactical Diversion for {corridor}", "type": "ai_route"},
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            }
        }

        return {
            "status": "Optimal Diversion Found",
            "route_geojson": route_geojson,
            "barricade_points": barricade_points,
            "blocked_construction_nodes": len(blocked_nodes)
        }

    except nx.NetworkXNoPath:
        logger.warning(f"No valid diversion found around {corridor}. Total Gridlock likely.")
        return {"status": "Gridlock - No Path", "route_geojson": None, "barricade_points": []}
    except Exception as e:
        logger.error(f"Routing Error: {e}")
        return {"status": "Error", "route_geojson": None, "barricade_points": []}

async def _get_construction_coordinates(corridor: str) -> list[tuple[float, float]]:
    coords = []
    try:
        async with AsyncSessionLocal() as session:
            query = text("""
                SELECT latitude, longitude 
                FROM active_construction_zones
                WHERE corridor ILIKE :c
            """)
            result = await session.execute(query, {"c": f"%{corridor}%"})
            for r in result.fetchall():
                if r.latitude and r.longitude:
                    coords.append((float(r.latitude), float(r.longitude)))
    except Exception as e:
        logger.error(f"Error fetching construction coordinates: {e}")
    return coords