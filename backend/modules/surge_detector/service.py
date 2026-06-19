import logging
from sqlalchemy import text
from database import engine
from datetime import datetime, timedelta

from modules.websockets.manager import notifier

logger = logging.getLogger(__name__)

# BUG FIX: State tracker to prevent the APScheduler from spamming the UI during long demos
_demo_alert_fired = False

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
    
    if std == 0:
        std = 1.0

    z_score = (current_incidents - mean) / std
    is_surge = z_score > 2.0  # 2 standard deviations = anomaly
    
    automated_action = None
    if is_surge:
        automated_action = (
            f"URGENT: Sudden gathering or severe bottleneck detected. "
            f"Z-Score: {z_score:.2f}. Immediate QR deployment recommended."
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
    APScheduler Daemon: Wakes up every 5 minutes to scan live ASTRAM data.
    """
    global _demo_alert_fired
    logger.info("[SURGE DAEMON] Waking up to scan ASTRAM live feeds...")
    
    live_data = [] 
    
    if not live_data and is_demo_mode:
        # BUG FIX: One-shot guard
        if _demo_alert_fired:
            logger.info("[SURGE DAEMON] Demo alert already fired this session, skipping to prevent UI spam.")
            return

        logger.info("[SURGE DAEMON] No live data found. Simulating live ASTRAM stream for demo...")
        demo_corridor = "Mysore Road"
        demo_incidents = 85  # Intentionally high to trigger the > 2.0 Z-Score
        
        try:
            surge_result = await check_for_surge(demo_corridor, demo_incidents)
            if surge_result["is_surge_detected"]:
                logger.warning(f"[AUTONOMOUS TRIGGER] Surge detected on {demo_corridor}: Z-Score {surge_result['z_score']}")
                logger.critical(f"[DISPATCH ALERT] {surge_result['automated_action']}")
                
                alert_payload = {
                    "type": "SURGE_ALERT",
                    "timestamp": datetime.now().isoformat(),
                    "source": "Autonomous_Surge_Daemon",
                    "corridor": demo_corridor,
                    "risk_level": "Critical",
                    "z_score": surge_result['z_score'],
                    "message": surge_result['automated_action'],
                    "ui_action": "TRIGGER_SIREN_AND_SNAP_MAP"
                }
                await notifier.broadcast_alert(alert_payload)
                
                # Mark as fired so it never triggers again during this session
                _demo_alert_fired = True

        except Exception as e:
            logger.error(f"Demo surge check failed: {e}")
        return

    # Production Logic: Process actual live database streams
    for row in live_data:
        try:
            surge_result = await check_for_surge(row.corridor, row.live_incident_count)
            if surge_result["is_surge_detected"]:
                logger.warning(f"[AUTONOMOUS TRIGGER] Surge detected on {row.corridor}: Z-Score {surge_result['z_score']}")
                logger.critical(f"[DISPATCH ALERT] {surge_result['automated_action']}")
                
                alert_payload = {
                    "type": "SURGE_ALERT",
                    "timestamp": datetime.now().isoformat(),
                    "source": "Autonomous_Surge_Daemon",
                    "corridor": row.corridor,
                    "risk_level": "Critical",
                    "z_score": surge_result['z_score'],
                    "message": surge_result['automated_action'],
                    "ui_action": "TRIGGER_SIREN_AND_SNAP_MAP"
                }
                await notifier.broadcast_alert(alert_payload)
        except Exception as e:
            continue