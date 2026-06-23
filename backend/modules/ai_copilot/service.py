"""
AI Copilot Service (Gemini Edition).
Gathers context from the Impact Forecaster and Compound Conflict Detector,
then uses Gemini to generate a tactical operational order.
Migrated to the new `google-genai` SDK.
"""
import logging
import asyncio
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime

# NEW SDK IMPORT
from google import genai

from config import GEMINI_API_KEY
from database import engine
from modules.impact_forecaster.service import predict
from modules.compound_conflict.service import detect_conflict

logger = logging.getLogger(__name__)

# Singleton cache to prevent re-initializing the client
_GEMINI_CLIENT = None

# The "Bouncer": Limits concurrent LLM API requests to prevent immediate rate limits
LLM_SEMAPHORE = asyncio.Semaphore(10)

def get_gemini_client():
    """Initializes and returns the modern GenAI Client."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
    return _GEMINI_CLIENT

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
    
    client = get_gemini_client()
    
    hour = event_datetime.hour
    dow = event_datetime.weekday()
    
    # 1. Gather Intelligence
    forecast = await predict(event_cause=event_cause, corridor=corridor, hour_of_day=hour, day_of_week=dow)
    conflict = await detect_conflict(corridor=corridor, event_cause=event_cause)
    stations = await _get_historical_stations(corridor=corridor)
    
    station_str = ", ".join(stations) if stations else "Nearest available station"
    warnings_str = "\n".join([f"- {w}" for w in conflict["warnings"]]) if conflict["warnings"] else "None"

    # 2. Build the System Prompt
    prompt = f"""
    You are an expert Traffic Operations Commander for the Bengaluru Traffic Police (BTP).
    Your task is to draft a structured, highly actionable Operational Order for an upcoming event.
    
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

    # 3. Call Gemini API asynchronously with Semaphore & Exponential Backoff
    logger.info(f"Generating Copilot order for {event_cause} at {corridor} using gemini-3.5-flash...")
    
    max_retries = 5
    async with LLM_SEMAPHORE:
        for attempt in range(max_retries):
            try:
                response = await client.aio.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt
                )
                return response.text
                
            except Exception as e:
                error_msg = str(e).lower()
                # If we hit a rate limit (429) or quota error, back off and retry
                if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg or "too many requests" in error_msg:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                    logger.warning(f"Gemini API rate limit hit. Retrying in {wait_time} seconds (Attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    # If it's a different error (like a bad API key), fail immediately
                    logger.error(f"Gemini API critical error: {e}")
                    raise HTTPException(status_code=502, detail=f"Failed to generate AI order: {str(e)}")
                    
        # If it fails 5 times in a row, return a safe fallback so the app doesn't crash
        logger.error("All retries exhausted for Gemini API. Falling back to default order.")
        return "⚠️ **LLM capacity exceeded due to high emergency volume.**\n\nStandard BTP tactical protocols apply. Please deploy available units from the nearest station and implement standard sector barricading."