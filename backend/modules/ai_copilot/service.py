"""
AI Copilot Service (Hugging Face Edition).
Gathers context from the Impact Forecaster and Compound Conflict Detector,
then uses a free open-source model to generate a tactical operational order.
"""
import logging
from huggingface_hub import AsyncInferenceClient
from sqlalchemy import text

from config import HUGGINGFACE_API_KEY
from database import engine
from modules.impact_forecaster.service import predict
from modules.compound_conflict.service import detect_conflict

logger = logging.getLogger(__name__)

# Initialize async client using a strong, free instruction-tuned model
client = AsyncInferenceClient(
    model="HuggingFaceH4/zephyr-7b-beta",
    token=HUGGINGFACE_API_KEY
)

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
    
    # 1. Gather Intelligence
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
    Keep it concise, authoritative, and formatted for quick reading by field officers. Do not add introductory fluff.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate the operational order based on the provided intelligence."}
    ]

    # 3. Call Hugging Face API
    logger.info(f"Generating Copilot order for {event_cause} at {corridor} using Hugging Face...")
    try:
        response = await client.chat_completion(
            messages=messages,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Hugging Face API error: {e}")
        return f"Error generating operational order: {str(e)}"