import logging
from sqlalchemy import text
from database import engine
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def check_for_surge(corridor: str, current_incidents: int) -> dict:
    """The core mathematical calculator (Z-Score logic)."""
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

    return {
        "corridor": corridor,
        "baseline_mean": round(mean, 2),
        "baseline_std": round(std, 2),
        "current_incidents": current_incidents,
        "z_score": round(z_score, 2),
        "is_surge_detected": is_surge,
        "automated_action": automated_action
    }


async def run_autonomous_surge_scan(is_demo_mode: bool = True):
    """
    The Autonomous Daemon. 
    Runs in the background, polls live data, and triggers actions without human input.
    """
    logger.info("[SURGE DAEMON] Waking up to poll live traffic streams...")

    # 1. Fetch live incident counts for the last hour across all corridors
    query = text("""
        SELECT corridor, COUNT(*) as live_incident_count
        FROM incidents
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        GROUP BY corridor
    """)

    async with engine.connect() as conn:
        result = await conn.execute(query)
        live_data = result.fetchall()

    # 2. Hackathon Demo Fallback
    # If the database only has historical CSV data, the query above will return empty.
    # This block simulates a live ASTRAM stream catching a sudden gathering.
    if not live_data and is_demo_mode:
        logger.info("[SURGE DAEMON] No live data found. Simulating live ASTRAM stream for demo...")
        demo_corridor = "Mysore Road"
        demo_incidents = 85  # Intentionally high to trigger the > 2.0 Z-Score
        
        try:
            surge_result = await check_for_surge(demo_corridor, demo_incidents)
            if surge_result["is_surge_detected"]:
                logger.warning(f"[AUTONOMOUS TRIGGER] Surge detected on {demo_corridor}: Z-Score {surge_result['z_score']}")
                logger.critical(f"[DISPATCH ALERT] {surge_result['automated_action']}")
                # In production, this is where you push an alert to a WebSocket or SMS API
        except Exception as e:
            logger.error(f"Demo surge check failed: {e}")
        return

    # 3. Production Logic: Process actual live database streams
    for row in live_data:
        try:
            surge_result = await check_for_surge(row.corridor, row.live_incident_count)
            if surge_result["is_surge_detected"]:
                logger.warning(f"[AUTONOMOUS TRIGGER] Surge detected on {row.corridor}: Z-Score {surge_result['z_score']}")
                logger.critical(f"[DISPATCH ALERT] {surge_result['automated_action']}")
        except ValueError:
            continue # Ignore corridors that don't have a baseline yet