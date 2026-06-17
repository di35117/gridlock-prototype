"""
Impact Forecaster service — loads trained LightGBM models from disk and
produces on-demand event impact forecasts. This is what closes Pain Point 1
("event impact is not quantified in advance").
"""

import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from database import engine
from modules.impact_forecaster import trainer
from modules.impact_forecaster.trainer import build_features

logger = logging.getLogger(__name__)

# ── In-memory model cache (loaded once, reused across requests) ───────
_priority_model = None
_closure_model = None
_encoders = None


def _ensure_models_loaded() -> None:
    global _priority_model, _closure_model, _encoders
    if _priority_model is None or _closure_model is None or _encoders is None:
        if not trainer.models_exist():
            raise RuntimeError(
                "Impact Forecaster models not found. Call POST /api/forecast/train first."
            )
        _priority_model, _closure_model, _encoders = trainer.load_models()
        logger.info("Impact Forecaster models loaded into memory.")


def reload_models() -> None:
    """Force a fresh load from disk — call this right after retraining."""
    global _priority_model, _closure_model, _encoders
    _priority_model, _closure_model, _encoders = trainer.load_models()
    logger.info("Impact Forecaster models reloaded.")


# ── Context lookups against the pre-computed tables ───────────────────

async def _get_corridor_context(corridor: str) -> dict:
    query = text("""
        SELECT closure_rate, high_priority_rate, risk_score
        FROM corridor_risk_profiles
        WHERE corridor ILIKE :corridor
        LIMIT 1
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        row = result.fetchone()
    if row is None:
        return {"closure_rate": 0.0, "high_priority_rate": 0.0, "risk_score": 0.0, "known": False}
    return {
        "closure_rate": float(row.closure_rate or 0.0),
        "high_priority_rate": float(row.high_priority_rate or 0.0),
        "risk_score": float(row.risk_score or 0.0),
        "known": True,
    }


async def _get_cause_context(event_cause: str) -> dict:
    query = text("""
        SELECT closure_rate, severity_tier
        FROM event_cause_stats
        WHERE event_cause ILIKE :cause
        LIMIT 1
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"cause": event_cause})
        row = result.fetchone()
    if row is None:
        return {"closure_rate": 0.0, "severity_tier": 1, "known": False}
    return {
        "closure_rate": float(row.closure_rate or 0.0),
        "severity_tier": int(row.severity_tier or 1),
        "known": True,
    }


def _classify_risk_level(compound_score: float) -> str:
    if compound_score >= 0.75:
        return "Critical"
    if compound_score >= 0.5:
        return "High"
    if compound_score >= 0.25:
        return "Medium"
    return "Low"


# ── Core prediction ─────────────────────────────────────────────────

async def predict(
    event_cause: str,
    corridor: str,
    hour_of_day: int | None = None,
    day_of_week: int | None = None,
    start_datetime: datetime | None = None,
) -> dict:
    _ensure_models_loaded()

    if start_datetime is not None:
        hour_of_day = start_datetime.hour
        day_of_week = start_datetime.weekday()

    if hour_of_day is None or day_of_week is None:
        raise ValueError("Provide start_datetime, or both hour_of_day and day_of_week.")

    corridor_ctx = await _get_corridor_context(corridor)
    cause_ctx = await _get_cause_context(event_cause)

    row = pd.DataFrame([{
        "event_cause": event_cause,
        "corridor": corridor,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "corridor_closure_rate": corridor_ctx["closure_rate"],
        "corridor_high_priority_rate": corridor_ctx["high_priority_rate"],
        "corridor_risk_score": corridor_ctx["risk_score"],
        "cause_closure_rate": cause_ctx["closure_rate"],
        "cause_severity_tier": cause_ctx["severity_tier"],
    }])

    X, _ = build_features(row, encoders=_encoders, fit=False)

    priority_proba = float(_priority_model.predict_proba(X)[0, 1])
    closure_proba = float(_closure_model.predict_proba(X)[0, 1])

    priority_pred = "High" if priority_proba >= 0.5 else "Low"
    closure_pred = closure_proba >= 0.5

    # Blends the model's own confidence with the corridor's empirical track
    # record — this is what lets a corridor with a bad history (e.g. Mysore
    # Road) still surface as high-risk even if the model itself is unsure.
    compound_score = (
        0.4 * priority_proba
        + 0.3 * closure_proba
        + 0.3 * corridor_ctx["risk_score"]
    )
    risk_level = _classify_risk_level(compound_score)

    return {
        "event_cause": event_cause,
        "corridor": corridor,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "priority_prediction": priority_pred,
        "priority_probability": round(priority_proba, 4),
        "closure_prediction": closure_pred,
        "closure_probability": round(closure_proba, 4),
        "corridor_risk_score": round(corridor_ctx["risk_score"], 4),
        "corridor_closure_rate": round(corridor_ctx["closure_rate"], 4),
        "corridor_high_priority_rate": round(corridor_ctx["high_priority_rate"], 4),
        "cause_closure_rate": round(cause_ctx["closure_rate"], 4),
        "cause_severity_tier": cause_ctx["severity_tier"],
        "compound_risk_score": round(compound_score, 4),
        "risk_level": risk_level,
        "known_corridor": corridor_ctx["known"],
        "known_cause": cause_ctx["known"],
    }