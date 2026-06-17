from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from modules.data_foundation.models import (
    CorridorRiskProfile, EventCauseStat, StationCorridorMapping
)
from modules.data_foundation.service import reload_data_foundation

router = APIRouter(prefix="/api/data", tags=["Data Foundation"])


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """
    Returns how many rows are loaded in each table.
    The frontend uses this to show a loading state on first boot.
    """
    tables = [
        "incidents",
        "corridor_risk_profiles",
        "station_corridor_mapping",
        "event_cause_stats",
    ]
    counts = {}
    for table in tables:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        counts[table] = result.scalar()

    return {"status": "ok", "record_counts": counts}


@router.get("/corridor-profiles")
async def get_corridor_profiles(db: AsyncSession = Depends(get_db)):
    """
    All corridor DNA profiles sorted by risk score descending.
    Used by the map layer to colour corridors and by the
    Compound Conflict Detector to compute combined risk.
    """
    result = await db.execute(
        select(CorridorRiskProfile)
        .order_by(CorridorRiskProfile.risk_score.desc())
    )
    profiles = result.scalars().all()

    return [
        {
            "corridor":               p.corridor,
            "total_incidents":        p.total_incidents,
            "road_closures":          p.road_closures,
            "closure_rate":           p.closure_rate,
            "high_priority_count":    p.high_priority_count,
            "high_priority_rate":     p.high_priority_rate,
            "event_incidents":        p.event_incidents,
            "construction_incidents": p.construction_incidents,
            "congestion_incidents":   p.congestion_incidents,
            "avg_hourly_baseline":    p.avg_hourly_baseline,
            "std_hourly_baseline":    p.std_hourly_baseline,
            "risk_score":             p.risk_score,
        }
        for p in profiles
    ]


@router.get("/corridor-profiles/{corridor}")
async def get_single_corridor_profile(
    corridor: str,
    db: AsyncSession = Depends(get_db),
):
    """Single corridor profile — used by the AI Copilot context builder."""
    result = await db.execute(
        select(CorridorRiskProfile)
        .where(CorridorRiskProfile.corridor == corridor)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor}' not found")

    return {
        "corridor":               profile.corridor,
        "total_incidents":        profile.total_incidents,
        "closure_rate":           profile.closure_rate,
        "high_priority_rate":     profile.high_priority_rate,
        "event_incidents":        profile.event_incidents,
        "construction_incidents": profile.construction_incidents,
        "avg_hourly_baseline":    profile.avg_hourly_baseline,
        "std_hourly_baseline":    profile.std_hourly_baseline,
        "risk_score":             profile.risk_score,
    }


@router.get("/event-stats")
async def get_event_stats(db: AsyncSession = Depends(get_db)):
    """
    Per-event-cause statistics sorted by incident count.
    Used by the Impact Forecaster and the AI Copilot.
    """
    result = await db.execute(
        select(EventCauseStat)
        .order_by(EventCauseStat.n_incidents.desc())
    )
    stats = result.scalars().all()

    return [
        {
            "event_cause":                s.event_cause,
            "n_incidents":                s.n_incidents,
            "closure_rate":               s.closure_rate,
            "high_priority_rate":         s.high_priority_rate,
            "median_time_to_close_hours": s.median_time_to_close_hours,
            "severity_tier":              s.severity_tier,
        }
        for s in stats
    ]


@router.get("/station-mapping/{corridor}")
async def get_station_mapping(
    corridor: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Which police stations handle a given corridor, sorted by
    incident count. The primary station is flagged.
    Used by the Resource Recommender.
    """
    result = await db.execute(
        select(StationCorridorMapping)
        .where(StationCorridorMapping.corridor == corridor)
        .order_by(StationCorridorMapping.incident_count.desc())
    )
    mappings = result.scalars().all()

    if not mappings:
        raise HTTPException(
            status_code=404,
            detail=f"No station mapping found for corridor '{corridor}'"
        )

    return [
        {
            "corridor":       m.corridor,
            "police_station": m.police_station,
            "incident_count": m.incident_count,
            "event_count":    m.event_count,
            "is_primary":     m.is_primary,
        }
        for m in mappings
    ]


@router.post("/reload")
async def reload_data():
    """
    Force a full reload from the CSV.
    Useful if the dataset is updated during development.
    Warning: truncates all incident data first.
    """
    result = await reload_data_foundation()
    return result