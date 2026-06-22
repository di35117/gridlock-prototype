# File: modules/routing_engine/service.py
import logging
import asyncio
import aiohttp
from sqlalchemy import text
from database import AsyncSessionLocal

from modules.mapmyindia_manager import mapmyindia_auth
from config import FRONTEND_URL

# PRODUCTION SCALE FIX: Import directly from root directory path instead of artificial app/ module
from http_client import http_pool

logger = logging.getLogger(__name__)

# PRODUCTION SCALE FIX: Concurrency control throttling limit to avoid upstream 429 rate limits
MAPS_SEMAPHORE = asyncio.Semaphore(20)

async def calculate_tactical_diversion(corridor: str, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    """
    Uses MapmyIndia Enterprise Routing API to calculate live diversions.
    Throttled by an asyncio Semaphore to handle sudden 100+ concurrent incident shocks.
    """
    logger.info(f"[Routing Engine] Request received for {corridor}. Queueing for API allocation...")
    
    try:
        token = await mapmyindia_auth.get_valid_token()
    except Exception as e:
        logger.error(f"Could not get MapmyIndia token: {e}")
        return {"status": "Error", "route_geojson": None, "barricade_points": []}
    
    coords_str = f"{o_lon},{o_lat};{d_lon},{d_lat}"
    url = f"https://apis.mapmyindia.com/advancedmaps/v1/{token}/route_adv/driving/{coords_str}?alternatives=true&geometries=geojson"
    
    headers = {"Referer": FRONTEND_URL}
    timeout = aiohttp.ClientTimeout(total=6) # Enforce responsive timeout limits
    
    # Enter throttling lock context
    async with MAPS_SEMAPHORE:
        try:
            # PRODUCTION SCALE FIX: Expanded guard check for uninitialized or closed session states
            if not http_pool.session or http_pool.session.closed:
                http_pool.start()
                
            async with http_pool.session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"MapmyIndia Routing API failed: {error_text}")
                    return {"status": "Error", "route_geojson": None, "barricade_points": []}
                
                data = await response.json()
                
                if not data.get("routes"):
                    logger.warning("No valid diversion path found by MapmyIndia.")
                    return {"status": "Gridlock - No Path", "route_geojson": None, "barricade_points": []}
                    
                best_route = data["routes"][0]
                
                route_geojson = {
                    "type": "Feature",
                    "properties": {"name": f"Tactical Diversion for {corridor}", "type": "enterprise_route"},
                    "geometry": best_route["geometry"]
                }
                barricade_points = [{"lat": o_lat, "lon": o_lon}]
                
                return {
                    "status": "Optimal Diversion Found",
                    "route_geojson": route_geojson,
                    "barricade_points": barricade_points,
                    "blocked_construction_nodes": 0
                }
        except asyncio.TimeoutError:
            logger.error(f"MapmyIndia Routing API timed out for corridor: {corridor}")
            return {"status": "Timeout Error", "route_geojson": None, "barricade_points": []}
        except Exception as e:
            logger.error(f"Routing Error: {e}")
            return {"status": "Error", "route_geojson": None, "barricade_points": []}

async def generate_network_metrics_geojson() -> dict:
    return {"type": "FeatureCollection", "features": []}

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