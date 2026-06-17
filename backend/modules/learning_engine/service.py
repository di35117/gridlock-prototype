"""
Learning Engine Service.
Processes post-event feedback to autonomously update calibration factors
using an Exponential Moving Average (EMA). Includes Google Maps polling logic.
"""
import logging
from datetime import datetime
import googlemaps

from config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

# Initialize Google Maps Client safely so the app doesn't crash if the key is missing
gmaps = None
if GOOGLE_MAPS_API_KEY:
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Google Maps client: {e}")

# In-memory calibration store for the demo.
# In production, this lives in PostgreSQL. Format: {(corridor, event_cause): calibration_factor}
_calibration_store = {}

async def poll_live_congestion(corridor_origin: str, corridor_dest: str, is_demo_mode: bool = True) -> float:
    """
    Polls Google Maps to calculate the real-time congestion ratio.
    Ratio > 1.0 means traffic is slower than normal.
    """
    if is_demo_mode or not gmaps:
        # HACKATHON DEMO MODE: Simulate a real-world congestion spike
        logger.info(f"[SIMULATION] Polling Google Maps for {corridor_origin}...")
        return 1.85  # Simulating that traffic is taking 85% longer than usual

    try:
        # PRODUCTION MODE: Real Google Maps API Call
        now = datetime.now()
        result = gmaps.distance_matrix(
            origins=[corridor_origin],
            destinations=[corridor_dest],
            mode="driving",
            departure_time=now
        )
        
        # Extract normal time vs time in current traffic
        leg = result['rows'][0]['elements'][0]
        
        # 'duration_in_traffic' is only returned if departure_time is provided
        if 'duration_in_traffic' not in leg:
            logger.warning("duration_in_traffic not returned by API. Falling back to baseline.")
            return 1.0
            
        normal_duration = leg['duration']['value']           # e.g., 600 seconds
        traffic_duration = leg['duration_in_traffic']['value'] # e.g., 1200 seconds
        
        if normal_duration == 0:
            return 1.0
            
        congestion_ratio = traffic_duration / normal_duration
        return congestion_ratio
        
    except Exception as e:
        logger.error(f"Google Maps API Error: {e}")
        return 1.0 # Default to baseline if API fails

async def process_learning_feedback(
    corridor: str, 
    event_cause: str, 
    predicted_risk: float, 
    observed_ratio: float = None
) -> dict:
    
    logger.info(f"Processing post-event learning for {event_cause} at {corridor}...")

    # If no real-world ratio is provided via the API payload, dynamically poll Google Maps
    if not observed_ratio:
        logger.info("No manual ratio provided. Triggering live Google Maps polling pipeline...")
        
        # We pass the corridor as the origin, and a mock destination for the distance matrix
        observed_ratio = await poll_live_congestion(
            corridor_origin=f"{corridor}, Bengaluru", 
            corridor_dest=f"{corridor} Junction, Bengaluru",
            is_demo_mode=True  # Set to False to hit the real Google Maps API
        )
    
    # 1. Fetch current calibration (Default is 1.0)
    key = (corridor, event_cause)
    current_cal = _calibration_store.get(key, 1.0)
    
    # 2. Calculate the correction needed
    # Example: If we predicted 1.0 but observed 1.85, the target correction is 1.85x
    correction = observed_ratio / max(predicted_risk, 0.1)  # Prevent division by zero
    
    # 3. Apply Exponential Moving Average (EMA) Update
    # Blend 70% historical knowledge with 30% new reality to prevent massive over-correction
    new_cal = (0.7 * current_cal) + (0.3 * correction)
    
    # Save back to state
    _calibration_store[key] = new_cal
    
    # 4. Generate the actionable insight for the dashboard
    if new_cal > 1.05:
        insight = f"Model under-predicted. {corridor} is more vulnerable to {event_cause} than baseline. Multiplier updated to {new_cal:.2f}x for future forecasts."
    elif new_cal < 0.95:
        insight = f"Model over-predicted. BTP handled {event_cause} exceptionally well on {corridor}. Multiplier reduced to {new_cal:.2f}x."
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