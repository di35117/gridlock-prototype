import logging
import json
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException

# Import your existing Gemini setup and other services
from modules.ai_copilot.service import get_gemini_model
from modules.impact_forecaster.service import predict
from modules.learning_engine.service import register_active_event

# NEW: Import the WebSocket Notifier
from modules.websockets.manager import notifier

logger = logging.getLogger(__name__)

async def process_osint_intel(raw_text: str, source: str) -> dict:
    logger.info(f"Processing OSINT intel from {source}...")
    
    model = get_gemini_model()
    
    # 1. Force Gemini to act as a Named Entity Recognition (NER) extractor
    prompt = f"""
    You are an intelligence extraction pipeline for the Bengaluru Traffic Police.
    Extract the event details from the following unstructured text.
    
    RAW TEXT: "{raw_text}"
    
    RULES:
    1. 'corridor' MUST be a major Bengaluru road (e.g., 'Mysore Road', 'ORR East 2'). If you cannot identify the road, default to 'Mysore Road'.
    2. 'event_cause' MUST be one of: 'public_event', 'VIP_movement', 'protest', 'procession', 'construction'.
    3. 'expected_crowd' MUST be an integer. Guess based on the text context if not explicit.
    4. 'hours_from_now' MUST be an integer representing when the event starts (e.g., 24 for tomorrow).
    5. 'duration_hours' MUST be an integer representing how long the event lasts.
    
    OUTPUT FORMAT: You must output ONLY a valid JSON object. No markdown, no backticks, no explanations.
    {{
        "corridor": "string",
        "event_cause": "string",
        "expected_crowd": integer,
        "hours_from_now": integer,
        "duration_hours": integer
    }}
    """
    
    try:
        response = await model.generate_content_async(prompt)
        raw_output = response.text.strip()
        
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3]
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3]
            
        extracted_data = json.loads(raw_output.strip())
        logger.info(f"OSINT Extraction successful: {extracted_data}")
        
    except Exception as e:
        logger.error(f"Failed to extract intel via Gemini: {e}")
        raise HTTPException(status_code=422, detail="Could not parse valid event data from the text.")

    # 2. Calculate Dates and Times
    start_time = datetime.now() + timedelta(hours=extracted_data.get("hours_from_now", 24))
    end_time = start_time + timedelta(hours=extracted_data.get("duration_hours", 4))
    
    # 3. Autonomously Forecast the Risk
    forecast = await predict(
        event_cause=extracted_data["event_cause"],
        corridor=extracted_data["corridor"],
        hour_of_day=start_time.hour,
        day_of_week=start_time.weekday()
    )
    predicted_risk = forecast["corridor_risk_score"]
    
    # 4. Autonomously Register the Event into the Learning Engine
    event_id = f"OSINT-{uuid.uuid4().hex[:6].upper()}"
    
    registration_result = await register_active_event(
        event_id=event_id,
        corridor=extracted_data["corridor"],
        event_cause=extracted_data["event_cause"],
        predicted_risk=predicted_risk,
        expected_end_time=end_time
    )

    # 5. NEW: Real-Time WebSocket Broadcast to React Dashboard
    alert_payload = {
        "type": "CRITICAL_ALERT",
        "timestamp": datetime.now().isoformat(),
        "source": f"OSINT_Harvester ({source})",
        "corridor": extracted_data["corridor"],
        "risk_level": forecast["risk_level"],
        "predicted_closure_probability": forecast["closure_probability"],
        "message": f"High-risk {extracted_data['event_cause']} detected via {source}. Barricade routing required.",
        "ui_action": "TRIGGER_SIREN_AND_SNAP_MAP"
    }
    await notifier.broadcast_alert(alert_payload)

    return {
        "status": "OSINT Processing Complete",
        "extracted_data": {
            "event_id": event_id,
            "corridor": extracted_data["corridor"],
            "event_cause": extracted_data["event_cause"],
            "expected_crowd": extracted_data["expected_crowd"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        },
        "forecasted_risk": predicted_risk,
        "registration_message": registration_result["message"]
    }