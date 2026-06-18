"""
AI Copilot Service (Gemini Edition).
Gathers context from the Impact Forecaster and Compound Conflict Detector,
then uses Gemini to generate a tactical operational order.
Includes auto-resolution for regional API key model availability.
"""
import logging
import google.generativeai as genai
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime

from config import GEMINI_API_KEY
from database import engine
from modules.impact_forecaster.service import predict
from modules.compound_conflict.service import detect_conflict

logger = logging.getLogger(__name__)

# Configure Gemini SDK
genai.configure(api_key=GEMINI_API_KEY)

# Singleton cache to prevent live network calls on every request
_CACHED_MODEL = None

def get_gemini_model():
    """Auto-discovers the best available model and caches it."""
    global _CACHED_MODEL
    if _CACHED_MODEL:
        return _CACHED_MODEL
        
    try:
        available_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1. Try to find the optimal 1.5 Flash model
        for m in available_models:
            if 'gemini-1.5-flash' in m.name:
                logger.info(f"Auto-selected model: {m.name}")
                _CACHED_MODEL = genai.GenerativeModel(m.name)
                return _CACHED_MODEL
                
        # 2. Try 1.5 Pro
        for m in available_models:
            if 'gemini-1.5-pro' in m.name:
                logger.info(f"Auto-selected model: {m.name}")
                _CACHED_MODEL = genai.GenerativeModel(m.name)
                return _CACHED_MODEL
                
        # 3. Fallback to whatever text model is available
        if available_models:
            logger.info(f"Fallback auto-selected model: {available_models[0].name}")
            _CACHED_MODEL = genai.GenerativeModel(available_models[0].name)
            return _CACHED_MODEL
            
        raise ValueError("No valid text generation models found for this API key.")
    except Exception as e:
        logger.error(f"Model auto-discovery failed: {e}")
        # Absolute hardcoded fallback
        _CACHED_MODEL = genai.GenerativeModel('models/gemini-1.5-flash')
        return _CACHED_MODEL

async def _get_historical_stations(corridor: str) -> list[str]:
    """Fetch which stations historically handle this corridor."""
    query = text("""
        SELECT police_station FROM station_corridor_mapping
        WHERE corridor ILIKE :corridor
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        rows = result.fetchall()
    return [row.police_station for row in rows if row.police_station]

async def generate_operational_order(
    event_cause: str,
    corridor: str,
    expected_crowd: int,
    event_details: str,
    event_datetime: datetime
) -> str:
    
    model = get_gemini_model()
    
    # Extract dynamic time parameters instead of hardcoding
    hour = event_datetime.hour
    dow = event_datetime.weekday()
    
    # 1. Gather Intelligence based on the actual requested time
    forecast = await predict(event_cause=event_cause, corridor=corridor, hour_of_day=hour, day_of_week=dow)
    conflict = await detect_conflict(corridor=corridor, event_cause=event_cause)
    stations = await _get_historical_stations(corridor=corridor)
    
    station_str = ", ".join(stations) if stations else "Nearest available station"
    warnings_str = "\n".join([f"- {w}" for w in conflict["warnings"]]) if conflict["warnings"] else "None"

    # 2. Build the System Prompt Context
    prompt = f"""
    You are an expert Traffic Operations Commander for the Bengaluru Traffic Police (BTP).
    Your task is to draft a structured, highly actionable Operational Order for an upcoming event.
    
    You MUST base your recommendations on the following data-grounded intelligence from our platform:
    
    --- INTELLIGENCE BRIEF ---
    Location: {corridor}
    Event Type: {event_cause}
    Event Time: {event_datetime.strftime("%Y-%m-%d %H:%M")}
    Expected Crowd: {expected_crowd}
    Additional Details: {event_details}
    
    MODEL FORECASTS:
    - Base Corridor Risk: {forecast['corridor_risk_score']}
    - Expected Closure Probability: {forecast['closure_probability'] * 100:.1f}%
    - Priority Assessment: {forecast['priority_prediction']}
    
    INFRASTRUCTURE CONFLICTS:
    - Compound Risk Score: {conflict['compound_risk_score']} (Multiplier: {conflict['compound_multiplier']}x)
    - Active Construction Zones: {conflict['construction_incident_count']}
    - System Warnings:
    {warnings_str}
    
    HISTORICAL DEPLOYMENT:
    - Recommended Primary Stations: {station_str}
    --------------------------
    
    Output a professional Operational Order using Markdown. Use clear headings: 
    1. Threat Assessment, 2. Station Deployment, 3. Barricading & Diversion Strategy, and 4. Action Checklist.
    Keep it concise, authoritative, and formatted for quick reading by field officers. Do not add introductory fluff.
    """

    # 3. Call Gemini API asynchronously
    logger.info(f"Generating Copilot order for {event_cause} at {corridor} using {model.model_name}...")
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        # Properly reject the request so the frontend can display an error state
        raise HTTPException(status_code=502, detail=f"Failed to generate AI order. Check API Key configuration. Error: {str(e)}")