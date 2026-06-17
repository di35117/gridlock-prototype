"""
Trains two LightGBM classifiers on all 8,173 ASTRAM incidents:
  1. Priority classifier     — predicts High / Low priority
  2. Road closure classifier — predicts whether road closure is required

Features come from both the raw incidents table and the pre-computed
corridor_risk_profiles + event_cause_stats tables (enrichment join).
"""

import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import lightgbm as lgb
from sqlalchemy import text

from database import engine

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
MODELS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "models"
)

PRIORITY_MODEL_PATH = MODELS_DIR / "priority_classifier.joblib"
CLOSURE_MODEL_PATH  = MODELS_DIR / "closure_classifier.joblib"
ENCODERS_PATH       = MODELS_DIR / "encoders.joblib"


# ── Data fetching ──────────────────────────────────────────────────────

async def fetch_training_data() -> pd.DataFrame:
    """
    Join incidents with pre-computed profiles to build enriched feature set.
    Runs a single SQL query — fast even at 8k rows.
    """
    query = text("""
        SELECT
            i.event_cause,
            i.corridor,
            i.hour_of_day,
            i.day_of_week,
            i.priority,
            i.requires_road_closure,
            COALESCE(c.closure_rate,        0.0) AS corridor_closure_rate,
            COALESCE(c.high_priority_rate,  0.0) AS corridor_high_priority_rate,
            COALESCE(c.risk_score,          0.0) AS corridor_risk_score,
            COALESCE(e.closure_rate,        0.0) AS cause_closure_rate,
            COALESCE(e.severity_tier,         1) AS cause_severity_tier
        FROM incidents i
        LEFT JOIN corridor_risk_profiles c ON i.corridor    = c.corridor
        LEFT JOIN event_cause_stats      e ON i.event_cause = e.event_cause
        WHERE i.event_cause IS NOT NULL
          AND i.priority    IS NOT NULL
          AND i.hour_of_day IS NOT NULL
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query)
        rows   = result.fetchall()
        df     = pd.DataFrame(rows, columns=list(result.keys()))
    return df


# ── Feature engineering ────────────────────────────────────────────────

FEATURE_COLS = [
    "event_cause_enc",
    "corridor_enc",
    "hour_of_day",
    "day_of_week",
    "corridor_closure_rate",
    "corridor_high_priority_rate",
    "corridor_risk_score",
    "cause_closure_rate",
    "cause_severity_tier",
]


def build_features(
    df: pd.DataFrame,
    encoders: dict | None = None,
    fit: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """
    Return (X, encoders).
    Pass fit=True on training; fit=False + encoders at inference.
    Unknown categories at inference get encoded as -1 (LightGBM handles this).
    """
    df = df.copy()
    df["corridor"]    = df["corridor"].fillna("Non-corridor")
    df["event_cause"] = df["event_cause"].fillna("unknown")

    if fit:
        encoders = {
            "event_cause": LabelEncoder(),
            "corridor":    LabelEncoder(),
        }
        df["event_cause_enc"] = encoders["event_cause"].fit_transform(df["event_cause"])
        df["corridor_enc"]    = encoders["corridor"].fit_transform(df["corridor"])
    else:
        def safe_transform(enc: LabelEncoder, values: pd.Series) -> np.ndarray:
            known = set(enc.classes_)
            return np.array([
                int(enc.transform([v])[0]) if v in known else -1
                for v in values
            ])
        df["event_cause_enc"] = safe_transform(encoders["event_cause"], df["event_cause"])
        df["corridor_enc"]    = safe_transform(encoders["corridor"],    df["corridor"])

    X = df[FEATURE_COLS].fillna(0).astype(float)
    return X, encoders


# ── Training ───────────────────────────────────────────────────────────

async def train_and_save() -> dict:
    """
    Full training pipeline:
      1. Fetch enriched data from DB
      2. Build features + encode labels
      3. Train priority + closure LightGBM classifiers
      4. Evaluate on 20% hold-out
      5. Save models + encoders to disk
    Returns a metrics dict.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching training data …")
    df = await fetch_training_data()
    logger.info(f"Training rows: {len(df)}")

    # Targets
    y_priority = (df["priority"] == "High").astype(int)
    y_closure  = df["requires_road_closure"].astype(int)

    # Features
    X, encoders = build_features(df, fit=True)

    # Train / validation split (stratify on priority for balance)
    X_tr, X_val, yp_tr, yp_val, yc_tr, yc_val = train_test_split(
        X, y_priority, y_closure,
        test_size=0.2,
        random_state=42,
        stratify=y_priority,
    )

    lgb_params = dict(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        #is_unbalance=True,
        random_state=42,
        verbose=-1,
    )

    logger.info("Training priority classifier …")
    priority_model = lgb.LGBMClassifier(**lgb_params)
    priority_model.fit(
        X_tr, yp_tr,
        eval_set=[(X_val, yp_val)],
        callbacks=[lgb.early_stopping(30, verbose=False),
                   lgb.log_evaluation(period=-1)],
    )

    logger.info("Training road-closure classifier …")
    closure_model = lgb.LGBMClassifier(**lgb_params)
    closure_model.fit(
        X_tr, yc_tr,
        eval_set=[(X_val, yc_val)],
        callbacks=[lgb.early_stopping(30, verbose=False),
                   lgb.log_evaluation(period=-1)],
    )

    # Metrics
    def _metrics(model, X_v, y_v, name):
        acc = accuracy_score(y_v, model.predict(X_v))
        try:
            auc = roc_auc_score(y_v, model.predict_proba(X_v)[:, 1])
        except Exception:
            auc = None
        auc_str = f"{auc:.4f}" if auc is not None else "N/A"
        logger.info(f"{name} — acc={acc:.4f}  auc={auc_str}")
        return {"accuracy": round(acc, 4), "auc": round(auc, 4) if auc else None}

    priority_metrics = _metrics(priority_model, X_val, yp_val, "Priority")
    closure_metrics  = _metrics(closure_model,  X_val, yc_val, "Closure")

    # Persist
    joblib.dump(priority_model, PRIORITY_MODEL_PATH)
    joblib.dump(closure_model,  CLOSURE_MODEL_PATH)
    joblib.dump(encoders,       ENCODERS_PATH)
    logger.info(f"Models saved to {MODELS_DIR}")

    return {
        "training_samples": int(len(X_tr)),
        "priority":         priority_metrics,
        "closure":          closure_metrics,
        "feature_cols":     FEATURE_COLS,
    }


# ── Loading ────────────────────────────────────────────────────────────

def load_models() -> tuple:
    """Return (priority_model, closure_model, encoders)."""
    return (
        joblib.load(PRIORITY_MODEL_PATH),
        joblib.load(CLOSURE_MODEL_PATH),
        joblib.load(ENCODERS_PATH),
    )


def models_exist() -> bool:
    return (
        PRIORITY_MODEL_PATH.exists()
        and CLOSURE_MODEL_PATH.exists()
        and ENCODERS_PATH.exists()
    )