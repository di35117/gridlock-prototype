"""
Trains two LightGBM classifiers on all 8,173 ASTRAM incidents.
Implements Cyclic Time Encoding, Bayesian Hyperparameter Tuning (Optuna),
and High-Resolution Geographic/Contextual Features (police_station, veh_type, zone, lat/lon)
to maximize AUC and F2-Score.
"""

import logging
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, precision_recall_curve
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
METRICS_PATH        = MODELS_DIR / "model_metrics.json"

# ── Data fetching ──────────────────────────────────────────────────────
async def fetch_training_data() -> pd.DataFrame:
    query = text("""
        SELECT
            i.event_cause,
            i.corridor,
            i.police_station,
            i.veh_type,
            i.zone,
            i.latitude,
            i.longitude,
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
    "police_station_enc",
    "veh_type_enc",
    "zone_enc",
    "latitude",
    "longitude",
    "hour_of_day",
    "day_of_week",
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
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
    df = df.copy()
    
    # Handle Missing Values for the new columns
    df["corridor"]       = df["corridor"].fillna("Non-corridor")
    df["event_cause"]    = df["event_cause"].fillna("unknown")
    df["police_station"] = df["police_station"].fillna("unknown")
    df["veh_type"]       = df["veh_type"].fillna("unknown")
    df["zone"]           = df["zone"].fillna("unknown")
    df['latitude']       = pd.to_numeric(df['latitude'], errors='coerce').fillna(0.0)
    df['longitude']      = pd.to_numeric(df['longitude'], errors='coerce').fillna(0.0)

    # Trigonometric Cyclic Encoding for Time
    df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24.0)
    df['day_sin']  = np.sin(2 * np.pi * df['day_of_week'] / 7.0)
    df['day_cos']  = np.cos(2 * np.pi * df['day_of_week'] / 7.0)

    if fit:
        encoders = {
            "event_cause":    LabelEncoder(),
            "corridor":       LabelEncoder(),
            "police_station": LabelEncoder(),
            "veh_type":       LabelEncoder(),
            "zone":           LabelEncoder(),
        }
        df["event_cause_enc"]    = encoders["event_cause"].fit_transform(df["event_cause"])
        df["corridor_enc"]       = encoders["corridor"].fit_transform(df["corridor"])
        df["police_station_enc"] = encoders["police_station"].fit_transform(df["police_station"])
        df["veh_type_enc"]       = encoders["veh_type"].fit_transform(df["veh_type"])
        df["zone_enc"]           = encoders["zone"].fit_transform(df["zone"])
    else:
        def safe_transform(enc: LabelEncoder, values: pd.Series) -> np.ndarray:
            known = set(enc.classes_)
            return np.array([
                int(enc.transform([v])[0]) if v in known else -1
                for v in values
            ])
        df["event_cause_enc"]    = safe_transform(encoders["event_cause"], df["event_cause"])
        df["corridor_enc"]       = safe_transform(encoders["corridor"], df["corridor"])
        df["police_station_enc"] = safe_transform(encoders["police_station"], df["police_station"])
        df["veh_type_enc"]       = safe_transform(encoders["veh_type"], df["veh_type"])
        df["zone_enc"]           = safe_transform(encoders["zone"], df["zone"])

    X = df[FEATURE_COLS].fillna(0).astype(float)
    return X, encoders

# ── Training ───────────────────────────────────────────────────────────
async def train_and_save() -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching training data …")
    df = await fetch_training_data()
    
    y_priority = (df["priority"] == "High").astype(int)
    y_closure  = df["requires_road_closure"].astype(int)
    X, encoders = build_features(df, fit=True)

    X_tr, X_val, yp_tr, yp_val, yc_tr, yc_val = train_test_split(
        X, y_priority, y_closure,
        test_size=0.2,
        random_state=42,
        stratify=y_closure, 
    )

    logger.info("Training priority classifier …")
    priority_model = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, is_unbalance=True, random_state=42, verbose=-1)
    priority_model.fit(X_tr, yp_tr, eval_set=[(X_val, yp_val)], callbacks=[lgb.early_stopping(30, verbose=False)])

    logger.info("Initiating Bayesian Optuna Study for Closure Model…")
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 300),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 15, 63),
                'scale_pos_weight': trial.suggest_float('scale_pos_weight', 5.0, 25.0),
                'objective': 'binary',
                'random_state': 42,
                'verbose': -1
            }
            model = lgb.LGBMClassifier(**params)
            model.fit(X_tr, yc_tr)
            y_proba = model.predict_proba(X_val)[:, 1]
            
            precisions, recalls, _ = precision_recall_curve(yc_val, y_proba)
            denom = (4 * precisions[:-1] + recalls[:-1])
            f2_scores = np.divide((5 * precisions[:-1] * recalls[:-1]), denom, out=np.zeros_like(denom), where=denom!=0)
            return np.max(f2_scores) if len(f2_scores) > 0 else 0

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=15)
        best_params = study.best_params
        best_params.update({'objective': 'binary', 'random_state': 42, 'verbose': -1})
        logger.info(f"Optuna complete. Best params: {best_params}")

    except ImportError:
        logger.warning("Optuna not found. Falling back to default parameters.")
        best_params = {'n_estimators': 300, 'learning_rate': 0.05, 'is_unbalance': True, 'verbose': -1, 'random_state': 42}

    closure_model = lgb.LGBMClassifier(**best_params)
    closure_model.fit(X_tr, yc_tr, eval_set=[(X_val, yc_val)], callbacks=[lgb.early_stopping(30, verbose=False)])

    def _metrics(model, X_v, y_v, name, optimize_threshold=False):
        y_proba = model.predict_proba(X_v)[:, 1]
        threshold = 0.5
        
        if optimize_threshold and sum(y_v) > 0:
            precisions, recalls, thresholds = precision_recall_curve(y_v, y_proba)
            denom = (4 * precisions[:-1] + recalls[:-1])
            f2_scores = np.divide((5 * precisions[:-1] * recalls[:-1]), denom, out=np.zeros_like(denom), where=denom!=0)
            threshold = thresholds[np.argmax(f2_scores)]
            
        y_pred = (y_proba >= threshold).astype(int)
        acc = accuracy_score(y_v, y_pred)
        recall = recall_score(y_v, y_pred, zero_division=0)
        
        try:
            auc = roc_auc_score(y_v, y_proba)
        except Exception:
            auc = None
            
        auc_str = f"{auc:.4f}" if auc is not None else "N/A"
        logger.info(f"{name} — acc={acc:.4f}  auc={auc_str}  recall={recall:.4f} (Threshold: {threshold:.4f})")
        
        return {
            "accuracy": round(acc, 4), 
            "auc": round(auc, 4) if auc else None, 
            "recall": round(recall, 4),
            "applied_threshold": round(float(threshold), 4)
        }

    priority_metrics = _metrics(priority_model, X_val, yp_val, "Priority", optimize_threshold=False)
    closure_metrics  = _metrics(closure_model,  X_val, yc_val, "Closure", optimize_threshold=True)

    metrics_payload = {
        "training_samples": int(len(X_tr)),
        "priority":         priority_metrics,
        "closure":          closure_metrics,
        "feature_cols":     FEATURE_COLS,
    }

    joblib.dump(priority_model, PRIORITY_MODEL_PATH)
    joblib.dump(closure_model,  CLOSURE_MODEL_PATH)
    joblib.dump(encoders,       ENCODERS_PATH)
    
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_payload, f, indent=4)
        
    logger.info(f"Models and metrics saved to {MODELS_DIR}")
    return metrics_payload

# ── Loading ────────────────────────────────────────────────────────────
def load_models() -> tuple:
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