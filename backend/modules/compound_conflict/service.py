"""
Service for detecting compounding infrastructure conflicts,
specifically targeting the 'construction activities' requirement.
"""
import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

async def detect_conflict(corridor: str, event_cause: str) -> dict:
    # 1. Fetch the baseline risk profile for the corridor
    query_profile = text("""
        SELECT risk_score FROM corridor_risk_profiles
        WHERE corridor ILIKE :corridor LIMIT 1
    """)
    
    # 2. Count active/historical construction pressure on this specific corridor
    query_construction = text("""
        SELECT COUNT(*) as count FROM incidents
        WHERE corridor ILIKE :corridor AND event_cause = 'construction'
    """)
    
    # 3. Fetch the historical closure rate for this specific event cause
    query = text("""
        SELECT closure_rate, severity_tier
        FROM event_cause_stats
        WHERE event_cause = :event_cause LIMIT 1 
    """)

    async with engine.connect() as conn:
        prof_res = await conn.execute(query_profile, {"corridor": corridor})
        prof_row = prof_res.fetchone()
        base_risk = float(prof_row.risk_score) if prof_row else 0.0

        cons_res = await conn.execute(query_construction, {"corridor": corridor})
        cons_row = cons_res.fetchone()
        construction_count = int(cons_row.count) if cons_row else 0
        
        cause_res = await conn.execute(query_cause, {"event_cause": event_cause})
        cause_row = cause_res.fetchone()
        cause_closure_rate = float(cause_row.closure_rate) if cause_row and cause_row.closure_rate else 0.1

    # 4. Calculate the Compound Multiplier
    # Base is 1.0. The impact of construction is mathematically weighted by the inherent severity of the event.
    raw_multiplier = 1.0 + (construction_count * 0.05 * (1.0 + cause_closure_rate))
    multiplier = min(raw_multiplier, 2.5) # Capped at 2.5x to prevent runaway scaling

    compound_score = base_risk * multiplier

    # 5. Classify the Compounded Risk
    if compound_score >= 8.0:
        level = "Critical"
    elif compound_score >= 6.0:
        level = "High"
    elif compound_score >= 4.0:
        level = "Medium"
    else:
        level = "Low"

    # 6. Generate Actionable Warnings
    warnings = []
    if construction_count > 0:
        warnings.append(f"Compound Risk: {construction_count} active construction zones detected on {corridor}.")
        warnings.append(f"Baseline corridor risk multiplied by {multiplier:.2f}x due to infrastructure stress and event severity.")
        
        if construction_count > 10:
            warnings.append("SEVERE: Corridor is heavily degraded. Diversion routing is mandatory.")
            
    if cause_closure_rate > 0.4:
        warnings.append(f"High-severity event type ({event_cause}) drastically increases compound breakdown risk.")

    return {
        "corridor": corridor,
        "event_cause": event_cause,
        "base_risk_score": round(base_risk, 2),
        "construction_incident_count": construction_count,
        "cause_closure_rate": round(cause_closure_rate, 2),
        "compound_multiplier": round(multiplier, 2),
        "compound_risk_score": round(compound_score, 2),
        "risk_level": level,
        "warnings": warnings
    }