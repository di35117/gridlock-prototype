"""
AI Copilot Service.
Gathers context from the Impact Forecaster and Compound Conflict Detector,
then uses Claude to generate a tactical operational order.
"""
import logging
from anthropic import AsyncAnthropic
from sqlalchemy import text

from config import ANTHROPIC_API_KEY
from database import engine
from modules.impact_forecaster.service import predict
from modules.compound_conflict.service import detect_conflict

logger = logging.getLogger(__name__)

# Initialize async client
client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

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
    event_details: str
) -> str:
    
    # 1. Gather Intelligence (using defaults for hour/day to simulate a standard planned event)
    forecast = await predict(event_cause=event_cause, corridor=corridor, hour_of_day=18, day_of_week=5)
    conflict = await detect_conflict(corridor=corridor, event_cause=event_cause)
    stations = await _get_historical_stations(corridor=corridor)
    
    station_str = ", ".join(stations) if stations else "Nearest available station"
    warnings_str = "\n".join([f"- {w}" for w in conflict["warnings"]]) if conflict["warnings"] else "None"

    # 2. Build the System Prompt Context
    system_prompt = f"""
    You are an expert Traffic Operations Commander for the Bengaluru Traffic Police (BTP).
    Your task is to draft a structured, highly actionable Operational Order for an upcoming event.
    
    You MUST base your recommendations on the following data-grounded intelligence from our platform:
    
    --- INTELLIGENCE BRIEF ---
    Location: {corridor}
    Event Type: {event_cause}
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
    Do NOT invent fake officer counts; instead refer to 'Standard Tiered Deployment' based on the risk score.
    Keep it concise, authoritative, and formatted for quick reading by field officers.
    """

    # 3. Call Claude API
    logger.info(f"Generating Copilot order for {event_cause} at {corridor}...")
    try:
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": "Generate the operational order based on the provided intelligence."}
            ]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return f"Error generating operational order: {str(e)}"