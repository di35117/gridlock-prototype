"""
Learning Engine Service.
Processes post-event feedback to autonomously update calibration factors
using an Exponential Moving Average (EMA). Utilizes MapmyIndia APIs via 
the global connection pool for highly scalable ground-truth traffic analytics.
"""
import logging
import random
import json
import asyncio
import aiohttp
from datetime import datetime
import redis.asyncio as redis

# NEW IMPORTS FOR DB SYNC
from database import AsyncSessionLocal
from sqlalchemy import text

# PRODUCTION FIX: Import FRONTEND_URL for secure whitelisting and DEMO_MODE for central configuration
from config import REDIS_URL, MAPMYINDIA_STATIC_KEY, FRONTEND_URL, DEMO_MODE

# PRODUCTION SCALE FIX: Import directly from the root layout directory 
from http_client import http_pool

logger = logging.getLogger(__name__)

# Initialize async Redis client for persistent learning memory
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# PRODUCTION SCALE FIX: Prevent background daemon threads from blasting MapmyIndia simultaneously
BACKGROUND_SEMAPHORE = asyncio.Semaphore(5)

async def register_active_event(event_id: str, corridor: str, event_cause: str, predicted_risk: float, expected_end_time: datetime) -> dict:
    """Registers an event in Redis to be monitored by the autonomous daemon."""
    event_data = {
        "corridor": corridor,
        "event_cause": event_cause,
        "predicted_risk": predicted_risk,
        "expected_end_time": expected_end_time.isoformat()
    }
    
    await redis_client.set(f"active_event:{event_id}", json.dumps(event_data))
    logger.info(f"Event {event_id} registered for autonomous learning loop. Closes at {expected_end_time}.")
    
    return {"status": "success", "message": f"Event {event_id} queued for autonomous post-event analysis."}

async def poll_live_congestion(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, is_demo_mode: bool) -> float:
    """
    Enterprise Integration: Polls MapmyIndia Distance Matrix and Distance Matrix ETA APIs
    to compute an exact, live congestion ratio (Traffic Duration / Free-Flow Duration).
    """
    if is_demo_mode:
        logger.info("[DEMO MODE] Simulating live traffic data...")
        return random.uniform(1.3, 2.0)
        
    logger.info("Polling MapmyIndia Distance Matrix endpoints for true traffic ratio...")
    
    coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    base_url = f"https://apis.mapmyindia.com/advancedmaps/v1/{MAPMYINDIA_STATIC_KEY}/distance_matrix/driving/{coords}"
    eta_url = f"https://apis.mapmyindia.com/advancedmaps/v1/{MAPMYINDIA_STATIC_KEY}/distance_matrix_eta/driving/{coords}"
    
    headers = {"Referer": FRONTEND_URL}
    timeout = aiohttp.ClientTimeout(total=5) # Fail-fast threshold for background tasks
    
    # Enter throttling lock to decouple background analytics load from active dashboards
    async with BACKGROUND_SEMAPHORE:
        try:
            if not http_pool.session or http_pool.session.closed:
                http_pool.start()
                
            # 1. Fetch free-flow baseline duration using global session pool
            async with http_pool.session.get(base_url, headers=headers, timeout=timeout) as resp_base:
                if resp_base.status != 200:
                    logger.warning(f"MapmyIndia Base Matrix failed with status {resp_base.status}.")
                    return 1.0
                base_data = await resp_base.json()
                
            # 2. Fetch live traffic duration using global session pool
            async with http_pool.session.get(eta_url, headers=headers, timeout=timeout) as resp_eta:
                if resp_eta.status != 200:
                    logger.warning(f"MapmyIndia Traffic Matrix (ETA) failed with status {resp_eta.status}.")
                    return 1.0
                eta_data = await resp_eta.json()
            
            normal_time = float(base_data['results']['durations'][0][1])
            traffic_time = float(eta_data['results']['durations'][0][1])
            
            if normal_time > 0:
                congestion_ratio = traffic_time / normal_time
                logger.info(f"[Learning Engine] Successfully gathered ground-truth congestion ratio: {congestion_ratio:.2f}")
                return congestion_ratio
                
        except asyncio.TimeoutError:
            logger.error("MapmyIndia Distance Matrix request timed out.")
        except Exception as e:
            logger.error(f"MapmyIndia API Error: {e}")
            
    return 1.0 # Safe fallback

async def process_learning_feedback(corridor: str, event_cause: str, predicted_risk: float, observed_ratio: float = None, is_demo_mode: bool = False) -> dict:
    """The EMA Math engine. Calculates new multiplier and permanently saves to Redis."""
    logger.info(f"Processing post-event learning for {event_cause} at {corridor}...")

    if not observed_ratio:
        observed_ratio = await poll_live_congestion(
            origin_lat=12.9716, origin_lon=77.5946, 
            dest_lat=12.9218, dest_lon=77.6451,
            is_demo_mode=is_demo_mode
        )
    
    cal_key = f"calib:{corridor.lower()}:{event_cause.lower()}"
    current_cal_str = await redis_client.get(cal_key)
    current_cal = float(current_cal_str) if current_cal_str else 1.0
    
    safe_prediction = max(predicted_risk, 0.1)
    correction = observed_ratio / safe_prediction
    
    # EMA Equation: 70% history, 30% new reality
    new_cal = (0.7 * current_cal) + (0.3 * correction)
    await redis_client.set(cal_key, str(new_cal))
    
    # --- NEW: SYNC TO POSTGRES SO THE FRONTEND HEATMAP UPDATES! ---
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                UPDATE corridor_risk_profiles 
                SET risk_score = LEAST(risk_score * :mult, 1.0)
                WHERE corridor ILIKE :c
            """), {"mult": new_cal, "c": f"%{corridor}%"})
            await session.commit()
            logger.info(f"Database synced. Heatmap for {corridor} will now reflect learned risk.")
    except Exception as e:
        logger.error(f"Failed to sync learning to Postgres DB: {e}")

    if new_cal > 1.05:
        insight = f"Model under-predicted. {corridor} is highly vulnerable to {event_cause}. Multiplier updated to {new_cal:.2f}x."
    elif new_cal < 0.95:
        insight = f"Model over-predicted. Multiplier reduced to {new_cal:.2f}x."
    else:
        insight = "Model accurately calibrated. No significant adjustment needed."

    return {
        "corridor": corridor,
        "event_cause": event_cause,
        "predicted_severity": round(predicted_risk, 2),
        "observed_severity": round(observed_ratio, 2),
        "previous_calibration": round(current_cal, 2),
        "new_calibration_factor": round(new_cal, 2),
        "learning_insight": insight
    }

async def autonomous_event_learning_scan():
    """Finds events that have ended and resolves them concurrently via sub-tasks."""
    logger.info("[LEARNING DAEMON] Scanning for completed events...")
    
    try:
        keys = await redis_client.keys("active_event:*")
        now = datetime.now()
        tasks = []
        
        for key in keys:
            event_data_str = await redis_client.get(key)
            if not event_data_str:
                continue
                
            event_data = json.loads(event_data_str)
            end_time = datetime.fromisoformat(event_data["expected_end_time"])
            
            if now >= end_time:
                # PRODUCTION SCALE FIX: Schedule concurrent execution tasks safely
                tasks.append(_execute_and_purge_event(key, event_data))
                
        if tasks:
            logger.info(f"[LEARNING DAEMON] Bundling {len(tasks)} tasks for non-blocking execution loop...")
            await asyncio.gather(*tasks)
            
    except Exception as daemon_err:
        logger.error(f"[LEARNING DAEMON] Internal scan iteration failed: {daemon_err}")

async def _execute_and_purge_event(key: str, event_data: dict):
    """Isolated concurrent worker routine to safely evaluate metrics and clean up memory keys."""
    try:
        logger.info(f"[AUTONOMOUS LEARNING] Event {key} concluded. Initiating MapmyIndia poll & EMA update...")
        await process_learning_feedback(
            corridor=event_data["corridor"],
            event_cause=event_data["event_cause"],
            predicted_risk=event_data["predicted_risk"],
            observed_ratio=None, 
            is_demo_mode=DEMO_MODE 
        )
    finally:
        # Guarantee memory cleanup happens even if the API times out
        await redis_client.delete(key)