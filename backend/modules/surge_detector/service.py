import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

async def check_for_surge(corridor: str, current_incidents: int) -> dict:
    query = text("""
        SELECT avg_hourly_baseline, std_hourly_baseline 
        FROM corridor_risk_profiles 
        WHERE corridor ILIKE :corridor LIMIT 1
    """)
    
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        row = result.fetchone()
        
    if not row:
        raise ValueError(f"Corridor '{corridor}' not found in risk profiles.")
        
    mean = float(row.avg_hourly_baseline or 0.0)
    std = float(row.std_hourly_baseline or 1.0)
    
    # Prevent division by zero if a corridor has zero variance
    if std == 0:
        std = 1.0

    # Calculate Z-Score: (X - Mean) / Standard Deviation
    z_score = (current_incidents - mean) / std
    is_surge = z_score > 2.0  # 2 standard deviations = anomaly
    
    automated_action = None
    if is_surge:
        automated_action = (
            f"URGENT: Sudden gathering or severe bottleneck detected. "
            f"Incident volume is {z_score:.1f} standard deviations above normal. "
            f"Auto-dispatching nearest QRT (Quick Response Team) to {corridor}."
        )
        logger.warning(f"Surge detected on {corridor}: Z-Score {z_score:.2f}")

    return {
        "corridor": corridor,
        "baseline_mean": round(mean, 2),
        "baseline_std": round(std, 2),
        "current_incidents": current_incidents,
        "z_score": round(z_score, 2),
        "is_surge_detected": is_surge,
        "automated_action": automated_action
    }