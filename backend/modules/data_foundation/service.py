import logging
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from config import DATA_PATH
from database import engine
from modules.data_foundation.models import (
    Incident, CorridorRiskProfile, StationCorridorMapping, EventCauseStat
)

logger = logging.getLogger(__name__)

# Event causes that count as "event-driven" incidents
EVENT_CAUSES = {"public_event", "procession", "vip_movement", "protest"}

# ─────────────────────────────────────────────
# 1. CSV LOADING + CLEANING
# ─────────────────────────────────────────────

def _load_and_clean_csv() -> pd.DataFrame:
    """
    Read the ASTRAM CSV, normalise column names, parse dates,
    cast booleans, and derive hour_of_day / day_of_week /
    time_to_close_hours columns.
    """
    df = pd.read_csv(DATA_PATH, low_memory=False)

    # Normalise column names: lowercase, strip whitespace, spaces→underscores
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"\s+", "_", regex=True)
    )

    logger.info(f"CSV columns detected: {list(df.columns)}")

    # ── Datetime parsing ──────────────────────────────────────
    for col in ["start_datetime", "resolved_datetime", "closed_datetime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            if df[col].dt.tz is not None:
                df[col] = df[col].dt.tz_convert(None)

    # ── Boolean normalisation ─────────────────────────────────
    if "requires_road_closure" in df.columns:
        df["requires_road_closure"] = (
            df["requires_road_closure"]
            .map({True: True, False: False,
                  "True": True, "False": False,
                  "true": True, "false": False,
                  1: True, 0: False, "1": True, "0": False})
            .fillna(False)
            .astype(bool)
        )

    # ── Derived time features ─────────────────────────────────
    if "start_datetime" in df.columns:
        df["hour_of_day"] = df["start_datetime"].dt.hour.astype("Int64")
        df["day_of_week"] = df["start_datetime"].dt.dayofweek.astype("Int64")

    # ── Time-to-close (hours) ─────────────────────────────────
    if "closed_datetime" in df.columns and "start_datetime" in df.columns:
        diff = (df["closed_datetime"] - df["start_datetime"]).dt.total_seconds() / 3600
        df["time_to_close_hours"] = diff.where(diff > 0, other=np.nan)

    # ── Clean string columns ──────────────────────────────────
    str_cols = [
        "event_type", "event_cause", "priority", "status",
        "corridor", "zone", "police_station", "junction",
        "address", "description", "direction", "route_path",
        "assigned_to_police_id", "closed_by_id",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

    # Replace all remaining NaN/NaT with Python None for asyncpg
    df = df.where(pd.notnull(df), other=None)

    return df


# ─────────────────────────────────────────────
# 2. CHECK / INSERT INCIDENTS
# ─────────────────────────────────────────────

async def check_data_loaded() -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM incidents"))
        return result.scalar() > 0


async def _load_incidents(df: pd.DataFrame) -> int:
    """Batch-insert incident rows into PostgreSQL (skips duplicates)."""
    model_cols = [
        "id", "event_type", "event_cause",
        "start_datetime", "resolved_datetime", "closed_datetime",
        "priority", "requires_road_closure", "status",
        "corridor", "zone", "police_station", "junction",
        "address", "description", "latitude", "longitude",
        "assigned_to_police_id", "closed_by_id",
        "direction", "route_path",
        "hour_of_day", "day_of_week", "time_to_close_hours",
    ]

    # Only keep columns that actually exist in the CSV
    available = [c for c in model_cols if c in df.columns]
    records = df[available].to_dict(orient="records")

    # Convert numpy int64 / float64 to plain Python types (asyncpg requirement)
    clean = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = None if np.isnan(v) else float(v)
            elif isinstance(v, (np.bool_,)):
                v = bool(v)
            elif pd.isna(v) if not isinstance(v, (list, dict)) else False:
                v = None
            clean_row[k] = v
        clean.append(clean_row)

    BATCH = 500
    async with engine.begin() as conn:
        for i in range(0, len(clean), BATCH):
            batch = clean[i : i + BATCH]
            stmt = insert(Incident).on_conflict_do_nothing(index_elements=["id"])
            await conn.execute(stmt, batch)

    logger.info(f"Inserted {len(clean)} incidents")
    return len(clean)


# ─────────────────────────────────────────────
# 3. CORRIDOR RISK PROFILES
# ─────────────────────────────────────────────

async def _compute_corridor_profiles(df: pd.DataFrame):
    """
    Build a DNA risk profile for every corridor using all 8,173 records.
    Includes:
      - closure_rate, high_priority_rate
      - event_incidents, construction_incidents, congestion_incidents
      - hourly baseline mean + std  (powers the Surge Detector)
      - composite risk_score 0-10
    """
    # Drop non-corridor rows
    mask = df["corridor"].notna() & (df["corridor"] != "Non-corridor")
    dc = df[mask].copy()

    if dc.empty:
        logger.warning("No corridor data found — skipping corridor profiles")
        return

    # ── Per-corridor aggregates ───────────────────────────────
    grp = dc.groupby("corridor")

    profiles = pd.DataFrame({
        "corridor":               grp.groups.keys(),
        "total_incidents":        grp["id"].count().values,
        "road_closures":          grp["requires_road_closure"].sum().values,
        "high_priority_count":    grp["priority"].apply(lambda x: (x == "High").sum()).values,
        "event_incidents":        grp["event_cause"].apply(
                                      lambda x: x.isin(EVENT_CAUSES).sum()
                                  ).values,
        "construction_incidents": grp["event_cause"].apply(
                                      lambda x: (x == "construction").sum()
                                  ).values,
        "congestion_incidents":   grp["event_cause"].apply(
                                      lambda x: (x == "congestion").sum()
                                  ).values,
    })

    profiles["closure_rate"]       = (profiles["road_closures"]       / profiles["total_incidents"]).round(4)
    profiles["high_priority_rate"] = (profiles["high_priority_count"] / profiles["total_incidents"]).round(4)

    # ── Hourly baseline per corridor (for Surge Detector) ────
    if "hour_of_day" in dc.columns:
        hourly = (
            dc.groupby(["corridor", "hour_of_day"])["id"]
              .count()
              .reset_index(name="count")
        )
        hourly_stats = (
            hourly.groupby("corridor")["count"]
                  .agg(["mean", "std"])
                  .reset_index()
                  .rename(columns={"mean": "avg_hourly_baseline",
                                   "std":  "std_hourly_baseline"})
        )
        hourly_stats["std_hourly_baseline"] = hourly_stats["std_hourly_baseline"].fillna(0)
        profiles = profiles.merge(hourly_stats, on="corridor", how="left")
    else:
        profiles["avg_hourly_baseline"] = 0.0
        profiles["std_hourly_baseline"] = 0.0

    profiles["avg_hourly_baseline"] = profiles["avg_hourly_baseline"].fillna(0).round(4)
    profiles["std_hourly_baseline"] = profiles["std_hourly_baseline"].fillna(0).round(4)

    # ── Composite risk score 0-10 ─────────────────────────────
    denom = profiles["total_incidents"].clip(lower=1)
    profiles["risk_score"] = (
        profiles["closure_rate"]       * 4.0 +
        profiles["high_priority_rate"] * 3.0 +
        (profiles["event_incidents"]        / denom) * 2.0 +
        (profiles["construction_incidents"] / denom) * 1.0
    ).clip(upper=10).round(2)

    records = profiles.to_dict(orient="records")
    # Convert numpy types
    records = _cast_numpy(records)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE corridor_risk_profiles"))
        await conn.execute(insert(CorridorRiskProfile), records)

    logger.info(f"Corridor profiles computed for {len(records)} corridors")


# ─────────────────────────────────────────────
# 4. STATION-CORRIDOR MAPPING
# ─────────────────────────────────────────────

async def _compute_station_mapping(df: pd.DataFrame):
    """
    Derive which police stations historically handle which corridors.
    The is_primary flag marks the station with the most incidents
    on that corridor — used as the first recommendation by the
    Resource Recommender.
    """
    dc = df[
        df["corridor"].notna() &
        (df["corridor"] != "Non-corridor") &
        df["police_station"].notna()
    ].copy()

    # All-incident counts
    all_map = (
        dc.groupby(["corridor", "police_station"])["id"]
          .count()
          .reset_index(name="incident_count")
    )

    # Event-only counts
    event_df = dc[dc["event_cause"].isin(EVENT_CAUSES)]
    if not event_df.empty:
        ev_map = (
            event_df.groupby(["corridor", "police_station"])["id"]
                    .count()
                    .reset_index(name="event_count")
        )
        all_map = all_map.merge(ev_map, on=["corridor", "police_station"], how="left")
    else:
        all_map["event_count"] = 0

    all_map["event_count"] = all_map["event_count"].fillna(0).astype(int)

    # Mark primary station (highest incident count per corridor)
    max_counts = all_map.groupby("corridor")["incident_count"].transform("max")
    all_map["is_primary"] = (all_map["incident_count"] == max_counts)

    records = _cast_numpy(all_map.to_dict(orient="records"))

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE station_corridor_mapping"))
        await conn.execute(insert(StationCorridorMapping), records)

    logger.info(f"Station-corridor mapping: {len(records)} entries")


# ─────────────────────────────────────────────
# 5. EVENT CAUSE STATISTICS
# ─────────────────────────────────────────────

async def _compute_event_cause_stats(df: pd.DataFrame):
    """
    Aggregate statistics per event_cause.
    closure_rate and severity_tier are the two most important
    outputs — they drive the Impact Forecaster.
    """
    grp = df.groupby("event_cause")

    stats = pd.DataFrame({
        "event_cause":               list(grp.groups.keys()),
        "n_incidents":               grp["id"].count().values,
        "closure_rate":              grp["requires_road_closure"].mean().round(4).values,
        "high_priority_rate":        grp["priority"]
                                         .apply(lambda x: (x == "High").mean())
                                         .round(4).values,
        "median_time_to_close_hours": grp["time_to_close_hours"].median().round(2).values
                                      if "time_to_close_hours" in df.columns
                                      else [None] * grp.ngroups,
    })

    def _tier(row):
        if row["closure_rate"] > 0.5 or row["high_priority_rate"] > 0.6:
            return 3   # High
        if row["closure_rate"] > 0.2 or row["high_priority_rate"] > 0.3:
            return 2   # Medium
        return 1       # Low

    stats["severity_tier"] = stats.apply(_tier, axis=1)
    stats = stats.where(pd.notnull(stats), other=None)
    records = _cast_numpy(stats.to_dict(orient="records"))

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE event_cause_stats"))
        await conn.execute(insert(EventCauseStat), records)

    logger.info(f"Event cause stats computed for {len(records)} causes")


# ─────────────────────────────────────────────
# 6. HELPER
# ─────────────────────────────────────────────

def _cast_numpy(records: list[dict]) -> list[dict]:
    """Convert numpy scalars to plain Python types for asyncpg."""
    cleaned = []
    for row in records:
        clean = {}
        for k, v in row.items():
            if isinstance(v, np.integer):
                v = int(v)
            elif isinstance(v, np.floating):
                v = None if np.isnan(v) else float(v)
            elif isinstance(v, np.bool_):
                v = bool(v)
            elif isinstance(v, float) and np.isnan(v):
                v = None
            clean[k] = v
        cleaned.append(clean)
    return cleaned


# ─────────────────────────────────────────────
# 7. ORCHESTRATOR
# ─────────────────────────────────────────────

async def initialize_data_foundation() -> dict:
    """
    Called once on server startup.
    Skips re-loading if incidents table already has data.
    """
    if await check_data_loaded():
        logger.info("Data already loaded — skipping CSV import.")
        return {"status": "already_loaded"}

    logger.info("Initialising data foundation …")

    df = _load_and_clean_csv()
    logger.info(f"CSV read: {len(df)} rows, {len(df.columns)} columns")

    n = await _load_incidents(df)
    await _compute_corridor_profiles(df)
    await _compute_station_mapping(df)
    await _compute_event_cause_stats(df)

    logger.info("Data foundation ready.")
    return {
        "status":             "initialized",
        "incidents_loaded":   n,
        "corridors_profiled": int(df["corridor"].nunique()),
    }


async def reload_data_foundation() -> dict:
    """Force a full reload (used by the /reload endpoint)."""
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE incidents CASCADE"))
    return await initialize_data_foundation()