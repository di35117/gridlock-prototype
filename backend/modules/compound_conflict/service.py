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

    async with engine.connect() as conn:
        prof_res = await conn.execute(query_profile, {"corridor": corridor})
        prof_row = prof_res.fetchone()
        base_risk = float(prof_row.risk_score) if prof_row else 0.0

        cons_res = await conn.execute(query_construction, {"corridor": corridor})
        cons_row = cons_res.fetchone()
        construction_count = int(cons_row.count) if cons_row else 0

    # 3. Calculate the Compound Multiplier
    # Base is 1.0. Every construction incident adds a 5% multiplier to the base risk.
    # Capped at a 2.5x multiplier to prevent runaway scaling on ORR East 2 (which has 102 incidents).
    raw_multiplier = 1.0 + (construction_count * 0.05)
    multiplier = min(raw_multiplier, 2.5)

    compound_score = base_risk * multiplier

    # 4. Classify the Compounded Risk
    if compound_score >= 8.0:
        level = "Critical"
    elif compound_score >= 6.0:
        level = "High"
    elif compound_score >= 4.0:
        level = "Medium"
    else:
        level = "Low"

    # 5. Generate Actionable Warnings
    warnings = []
    if construction_count > 0:
        warnings.append(f"Compound Risk: {construction_count} active construction zones detected on {corridor}.")
        warnings.append(f"Baseline corridor risk multiplied by {multiplier:.2f}x due to infrastructure stress.")
        
        if construction_count > 10:
            warnings.append("SEVERE: Corridor is heavily degraded. Diversion routing is mandatory.")

    return {
        "corridor": corridor,
        "base_risk_score": round(base_risk, 2),
        "construction_incident_count": construction_count,
        "compound_multiplier": round(multiplier, 2),
        "compound_risk_score": round(compound_score, 2),
        "risk_level": level,
        "warnings": warnings
    }