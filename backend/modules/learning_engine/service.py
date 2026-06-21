"""
Learning Engine Service.
Processes post-event feedback to autonomously update calibration factors
using an Exponential Moving Average (EMA). Now features Redis persistence 
and a background daemon for true per-event learning lifecycle tracking.
"""
import logging
import random
import json
from datetime import datetime
import redis.asyncio as redis

from config import REDIS_URL

logger = logging.getLogger(__name__)

# Initialize async Redis client for persistent learning memory
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def register_active_event(event_id: str, corridor: str, event_cause: str, predicted_risk: float, expected_end_time: datetime) -> dict:
    """Registers an event in Redis to be monitored by the autonomous daemon."""
    event_data = {
        "corridor": corridor,
        "event_cause": event_cause,
        "predicted_risk": predicted_risk,
        "expected_end_time": expected_end_time.isoformat()
    }
    
    # Store in Redis with the 'active_event' prefix
    await redis_client.set(f"active_event:{event_id}", json.dumps(event_data))
    logger.info(f"Event {event_id} registered for autonomous learning loop. Closes at {expected_end_time}.")
    
    return {"status": "success", "message": f"Event {event_id} queued for autonomous post-event analysis."}


async def poll_live_congestion(corridor_origin: str, corridor_dest: str, is_demo_mode: bool) -> float:
    """
    Hackathon Bypass: Simulates polling live map data to calculate real-time congestion ratio.
    Bypasses paid Google APIs to maintain a sovereign, air-gapped system.
    """
    logger.info(f"[SIMULATION] Polling live map data for {corridor_origin} to {corridor_dest}...")
    
    # Simulate typical congestion spike between 1.3x and 2.0x normal traffic duration
    simulated_traffic_ratio = random.uniform(1.3, 2.0)
    
    return simulated_traffic_ratio


async def process_learning_feedback(corridor: str, event_cause: str, predicted_risk: float, observed_ratio: float = None, is_demo_mode: bool = False) -> dict:
    """The EMA Math engine. Calculates new multiplier and permanently saves to Redis."""
    logger.info(f"Processing post-event learning for {event_cause} at {corridor}...")

    if not observed_ratio:
        observed_ratio = await poll_live_congestion(
            corridor_origin=f"{corridor}, Bengaluru", 
            corridor_dest=f"{corridor} Junction, Bengaluru",
            is_demo_mode=is_demo_mode
        )
    
    # Fetch permanent memory from Redis
    cal_key = f"calib:{corridor.lower()}:{event_cause.lower()}"
    current_cal_str = await redis_client.get(cal_key)
    current_cal = float(current_cal_str) if current_cal_str else 1.0
    
    # Prevent division by zero mathematically
    safe_prediction = max(predicted_risk, 0.1)
    correction = observed_ratio / safe_prediction
    
    # EMA Equation: 70% history, 30% new reality
    new_cal = (0.7 * current_cal) + (0.3 * correction)
    
    # Save permanent state back to Redis
    await redis_client.set(cal_key, str(new_cal))
    
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
    """
    Background daemon function. 
    Finds events that have ended, runs the learning loop, and purges the active record.
    """
    logger.info("[LEARNING DAEMON] Scanning for completed events...")
    
    # Find all active events registered in Redis
    keys = await redis_client.keys("active_event:*")
    now = datetime.now()
    
    for key in keys:
        event_data_str = await redis_client.get(key)
        if not event_data_str:
            continue
            
        event_data = json.loads(event_data_str)
        end_time = datetime.fromisoformat(event_data["expected_end_time"])
        
        if now >= end_time:
            # Event has finished. Trigger the autonomous map polling and learning loop!
            logger.info(f"[AUTONOMOUS LEARNING] Event {key} concluded. Initiating map poll & EMA update...")
            
            await process_learning_feedback(
                corridor=event_data["corridor"],
                event_cause=event_data["event_cause"],
                predicted_risk=event_data["predicted_risk"],
                observed_ratio=None, 
                is_demo_mode=True # Defaulting to demo mode for safe hackathon presentation
            )
            
            # Clean up the completed event
            await redis_client.delete(key)