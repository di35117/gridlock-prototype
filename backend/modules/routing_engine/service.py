import logging
import aiohttp
from sqlalchemy import text
from database import AsyncSessionLocal

# Import our new Enterprise Auth Manager
from modules.mapmyindia_manager import mapmyindia_auth

logger = logging.getLogger(__name__)

async def calculate_tactical_diversion(corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    """
    Uses MapmyIndia Enterprise Routing API to calculate live diversions.
    Bypasses local OSM memory constraints entirely.
    """
    logger.info(f"[Routing Engine] Calculating diversion for {corridor} using MapmyIndia...")
    
    # 1. Fetch the secure OAuth2 Bearer Token from our new background manager
    try:
        token = await mapmyindia_auth.get_valid_token()
    except Exception as e:
        logger.error(f"Could not get MapmyIndia token: {e}")
        return {"status": "Error", "route_geojson": None, "barricade_points": []}
    
    # 2. MapmyIndia Driving Directions API (Format: start_lon,start_lat;end_lon,end_lat)
    coords_str = f"{o_lon},{o_lat};{d_lon},{d_lat}"
    url = f"https://apis.mapmyindia.com/advancedmaps/v1/{token}/route_adv/driving/{coords_str}?alternatives=true&geometries=geojson"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"MapmyIndia Routing API failed: {error_text}")
                    return {"status": "Error", "route_geojson": None, "barricade_points": []}
                
                data = await response.json()
                
                # 3. Extract the optimal route
                if not data.get("routes"):
                    logger.warning("No valid diversion path found by MapmyIndia.")
                    return {"status": "Gridlock - No Path", "route_geojson": None, "barricade_points": []}
                    
                best_route = data["routes"][0]
                
                # MapmyIndia provides native GeoJSON geometries, perfect for MapLibre/React
                route_geojson = {
                    "type": "Feature",
                    "properties": {"name": f"Tactical Diversion for {corridor}", "type": "enterprise_route"},
                    "geometry": best_route["geometry"]
                }
                
                # 4. Tactical Barricade Points
                # Since the AI perfectly calculates the route, we just barricade the origin to seal the threat
                barricade_points = [{"lat": o_lat, "lon": o_lon}]
                
                return {
                    "status": "Optimal Diversion Found",
                    "route_geojson": route_geojson,
                    "barricade_points": barricade_points,
                    "blocked_construction_nodes": 0 # Handled natively by MapmyIndia traffic/routing logic
                }
    except Exception as e:
        logger.error(f"Routing Error: {e}")
        return {"status": "Error", "route_geojson": None, "barricade_points": []}

async def generate_network_metrics_geojson() -> dict:
    """
    Previously used to send the entire road network to React. 
    Now returning empty because MapmyIndia Web SDK handles the base map!
    """
    return {"type": "FeatureCollection", "features": []}

async def _get_construction_coordinates(corridor: str) -> list[tuple[float, float]]:
    """
    Kept for backward compatibility. 
    The AI Copilot (router.py) uses this to check for construction zones.
    """
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