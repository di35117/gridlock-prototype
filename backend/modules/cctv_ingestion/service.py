import logging
import json
import uuid
from datetime import datetime, timedelta

# Import the NEW client setup
from modules.ai_copilot.service import get_gemini_client
from modules.impact_forecaster.service import predict
from modules.websockets.manager import notifier
from modules.learning_engine.service import register_active_event

logger = logging.getLogger(__name__)

async def process_cctv_payload(raw_payload: dict):
    logger.info("Evaluating CCTV schema...")

    normalized_data = {}

    required_keys = {"corridor", "event_cause", "latitude", "longitude"}
    if required_keys.issubset(raw_payload.keys()):
        logger.info("[CCTV] Payload matches BTP standard schema. Bypassing LLM translation.")
        normalized_data = raw_payload
    else:
        logger.info("[CCTV] Non-standard schema detected. Routing to Gemini Data Translator...")
        client = get_gemini_client()
        
        prompt = f"""
        You are a Universal Data Translator for the Bengaluru Traffic Police API.
        A proprietary CCTV computer vision system just sent us this raw JSON payload. 
        You must map their proprietary fields into our strict internal schema.

        RAW CCTV PAYLOAD:
        {json.dumps(raw_payload)}

        RULES:
        1. 'corridor' MUST be a major Bengaluru road. If missing, guess from the coordinates or return 'unknown'.
        2. 'event_cause' MUST be mapped to one of: 'congestion', 'vehicle_breakdown', 'accident', 'water_logging', 'construction', or 'others'.
        3. 'latitude' and 'longitude' MUST be floats (default 0.0).
        4. 'veh_type' MUST be mapped if the camera detected a vehicle class (e.g., 'heavy_vehicle', 'two_wheeler', 'bmtc_bus'). Default 'unknown'.

        OUTPUT EXACTLY VALID JSON ONLY (No markdown):
        {{
            "corridor": "string",
            "event_cause": "string",
            "latitude": float,
            "longitude": float,
            "veh_type": "string"
        }}
        """
        try:
            # Generate using the new SDK
            response = await client.aio.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            raw_output = response.text.strip()
            
            if raw_output.startswith("```json"): 
                raw_output = raw_output[7:-3]
            elif raw_output.startswith("```"): 
                raw_output = raw_output[3:-3]
            
            normalized_data = json.loads(raw_output.strip())
            logger.info(f"[CCTV] LLM Translation complete: {normalized_data}")
        except Exception as e:
            logger.error(f"[CCTV] Failed to normalize proprietary data: {e}")
            return

    # Mathematical Forecasting (LightGBM)
    now = datetime.now()
    try:
        forecast = await predict(
            event_cause=normalized_data.get("event_cause", "others"),
            corridor=normalized_data.get("corridor", "unknown"),
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            latitude=float(normalized_data.get("latitude", 0.0)),
            longitude=float(normalized_data.get("longitude", 0.0)),
            veh_type=normalized_data.get("veh_type", "unknown")
        )
    except Exception as e:
        logger.error(f"[CCTV] Impact Forecaster failed: {e}")
        return

    # Queue Learning Engine
    event_id = f"CCTV-{uuid.uuid4().hex[:6].upper()}"
    end_time = now + timedelta(hours=2)
    
    try:
        await register_active_event(
            event_id=event_id,
            corridor=normalized_data.get("corridor", "unknown"),
            event_cause=normalized_data.get("event_cause", "others"),
            predicted_risk=forecast["compound_risk_score"],
            expected_end_time=end_time
        )
        logger.info(f"[CCTV] Event {event_id} successfully queued in the Learning Engine.")
    except Exception as e:
        logger.error(f"[CCTV] Failed to register event to Learning Engine: {e}")

    # WebSocket Broadcast
    alert_payload = {
        "type": "CCTV_ANOMALY",
        "timestamp": now.isoformat(),
        "source": "CCTV_Vision_Node",
        "corridor": normalized_data.get("corridor", "unknown"),
        "risk_level": forecast["risk_level"],
        "predicted_closure_probability": forecast["closure_probability"],
        "message": f"CCTV Feed detected {normalized_data.get('event_cause')} involving {normalized_data.get('veh_type', 'a vehicle')}. Threat logged to autonomous tracking queue.",
        "ui_action": "TRIGGER_SIREN_AND_SNAP_MAP"
    }
    
    await notifier.broadcast_alert(alert_payload)
    logger.info(f"[CCTV] Threat {event_id} broadcasted to Command Center WebSockets.")