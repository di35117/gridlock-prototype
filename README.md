# Gridlock

**An autonomous, predictive command platform for the Bengaluru Traffic Police (BTP)**

Gridlock turns 8,173+ historical ASTRAM traffic incident records into a live decision-support system: it forecasts how a planned event will impact a road corridor *before* it happens, detects when overlapping construction and events compound into critical risk, autonomously ingests intel from CCTV feeds and social/news sources, recommends manpower and barricade deployment, computes diversion routes around blockages, and learns from real-world outcomes to keep getting more accurate — all streamed live to a command-center dashboard over WebSockets.

It was built as a modular FastAPI backend so that each capability (forecasting, routing, OSINT, learning, etc.) is an independent, swappable module behind a shared data foundation.

## The problem

BTP currently manages traffic operations reactively. There's no system that can answer, in advance: *if we approve this procession on Mysore Road at 6 PM on a Friday, how bad will it get, which station should respond, and is there already a construction zone nearby that will make it worse?* Gridlock closes that gap by combining a trained ML risk model, rule-based compound-risk math, optimization, and an LLM copilot into one pipeline.

## Core capabilities

| Module | What it does |
|---|---|
| **Data Foundation** | Loads and cleans the ASTRAM incident CSV into PostgreSQL on first boot; computes per-corridor risk DNA, station-corridor mappings, and per-event-cause statistics that every other module reads from. |
| **Impact Forecaster** | Two LightGBM classifiers (priority + road-closure), tuned with Optuna and trained on cyclic time, geography, vehicle-type, and historical corridor/cause features. Outputs a blended `compound_risk_score` and risk tier for any event before it happens. |
| **Compound Conflict Detector** | Detects when active construction zones on a corridor multiply the risk of a new event, capped at a 2.5x multiplier, and raises explicit warnings (e.g. "diversion routing is mandatory"). |
| **AI Copilot** | Calls Gemini to gather forecaster + conflict-detector context and draft a structured, field-ready Operational Order (threat assessment, station deployment, barricading strategy, action checklist). |
| **OSINT Harvester** | Accepts raw, unstructured text (news, social media, radio) — including via webhook from enterprise listening tools — and uses Gemini as a named-entity extractor to turn it into a structured event, forecast its risk, and broadcast an alert, all autonomously. |
| **CCTV Ingestion** | A plug-and-play webhook for third-party computer-vision camera systems. Matches a known schema instantly, or falls back to a Gemini-powered "universal data translator" for proprietary payloads, then feeds the result into the forecaster. |
| **Surge Detector** | Z-score anomaly detection against each corridor's historical hourly baseline; flags sudden incident spikes (>2σ) for immediate QR (Quick Response) team deployment. Includes an autonomous polling daemon. |
| **Resource Recommender** | Recommends primary/backup stations and a manpower tier per risk level, and uses linear programming (PuLP) to optimally allocate a limited officer pool across multiple simultaneous events by risk-weighted priority. |
| **Tactical Routing Engine** | Loads a Bengaluru road network graph (OSMnx/NetworkX), removes nodes near active construction, and computes a diversion route plus barricade placement points as GeoJSON for the map UI. |
| **Learning Engine** | Registers events in Redis when they're created, and once they conclude, autonomously polls live Google Maps congestion data and runs an exponential-moving-average correction against the original forecast — so the model's calibration improves over time without retraining. |
| **WebSockets** | A connection manager that broadcasts every alert (surge, OSINT, CCTV) instantly to all connected dashboard clients. |

## Architecture

```
┌─────────────┐   ┌──────────────┐
│ CCTV Webhook│   │ OSINT Webhook│      (autonomous intake)
└──────┬──────┘   └──────┬───────┘
       │  raw JSON        │  raw text
       ▼                  ▼
  Gemini schema      Gemini NER
  normalization       extraction
       │                  │
       └────────┬─────────┘
                 ▼
      Impact Forecaster (LightGBM)
                 │
                 ▼
      Compound Conflict Detector
                 │
        ┌────────┴─────────┐
        ▼                  ▼
 Resource Recommender   Routing Engine
   (PuLP optimizer)    (OSMnx/NetworkX)
        │                  │
        └────────┬─────────┘
                 ▼
        WebSocket broadcast → React dashboard
                 │
                 ▼
        Learning Engine (Redis EMA)
        closes the loop on event end
```

All feature modules read shared, pre-computed corridor/event statistics from the **Data Foundation** layer instead of re-scanning raw incident data on every request.

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI (async), Pydantic v2 |
| Database | PostgreSQL via SQLAlchemy (async) + asyncpg |
| Cache / state | Redis (async client) — powers the Learning Engine's calibration memory |
| Machine learning | LightGBM, scikit-learn, Optuna (Bayesian hyperparameter tuning), pandas/numpy |
| Generative AI | Google Gemini (`google-genai` SDK) — copilot drafting, schema translation, NER extraction |
| Optimization | PuLP (CBC solver) for linear-programming manpower allocation |
| Routing | OSMnx + NetworkX over a cached Bengaluru road graph |
| Live traffic data | Google Maps Distance Matrix API |
| Real-time transport | Native FastAPI WebSockets |

## Project structure

```
backend/
└── modules/
    ├── ai_copilot/           # Gemini-drafted operational orders
    ├── cctv_ingestion/       # Autonomous CCTV webhook + LLM normalization
    ├── compound_conflict/    # Construction × event risk multiplier
    ├── data_foundation/      # CSV → PostgreSQL ETL, corridor/event stats
    ├── impact_forecaster/    # LightGBM training + inference
    ├── learning_engine/      # Redis-backed EMA self-calibration
    ├── osint_harvester/      # Unstructured text → structured event pipeline
    ├── resource_recommender/ # Station assignment + LP manpower optimizer
    ├── routing_engine/       # Graph-based diversion routing
    ├── surge_detector/       # Z-score anomaly detection
    └── websockets/           # Connection manager + dashboard endpoint
```

Each feature module follows the same internal pattern: `models.py` (Pydantic schemas), `router.py` (FastAPI routes), `service.py` (business logic), `__init__.py`. `impact_forecaster` additionally has `trainer.py` for model training.

## API reference

All routes are mounted under `/api`. Replace `{corridor}` with a URL-encoded corridor name (e.g. `Mysore Road`).

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/data/status` | Row counts for each core table — used for dashboard boot state |
| `GET` | `/api/data/corridor-profiles` | All corridor risk profiles, sorted by risk |
| `GET` | `/api/data/corridor-profiles/{corridor}` | Single corridor profile |
| `GET` | `/api/data/event-stats` | Per-event-cause statistics |
| `GET` | `/api/data/station-mapping/{corridor}` | Police stations historically handling a corridor |
| `POST` | `/api/data/reload` | Force a full CSV reload (truncates incident data) |
| `GET` | `/api/forecast/status` | Whether trained models exist |
| `GET` | `/api/forecast/metrics` | Trained model performance metrics |
| `POST` | `/api/forecast/train` | Train/retrain the priority + closure classifiers |
| `POST` | `/api/forecast/predict` | Forecast an event's impact (priority, closure probability, risk tier) |
| `POST` | `/api/conflict/detect` | Compute compound risk from construction + event severity |
| `POST` | `/api/copilot/generate` | Generate a Gemini-drafted Operational Order |
| `POST` | `/api/osint/process` | Manually process raw OSINT text into a forecasted event |
| `POST` | `/api/osint/webhook` | Autonomous webhook for social-listening tools |
| `POST` | `/api/cctv/webhook` | Autonomous webhook for CCTV vision systems |
| `POST` | `/api/surge/check` | Z-score surge check against a corridor's hourly baseline |
| `POST` | `/api/recommend/tactical` | Station + manpower tier + barricade count recommendation |
| `POST` | `/api/recommend/optimize` | LP-optimized officer allocation across multiple events |
| `POST` | `/api/routing/diversion` | Diversion route + barricade points avoiding construction |
| `POST` | `/api/learning/register` | Register an active event for post-event learning |
| `POST` | `/api/learning/feedback` | Manually trigger the EMA calibration update |
| `WS` | `/api/ws/dashboard` | Real-time alert stream for the frontend dashboard |

## Getting started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- A Gemini API key
- A Google Maps API key (optional — falls back to simulated congestion data in demo mode)
- The ASTRAM incident CSV and a pre-downloaded Bengaluru road graph (`.graphml`) for the routing engine

### Environment variables

The modules import these from a root-level `config.py` / `database.py` (not included in this archive — add them at the project root):

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gridlock
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your-gemini-key
GOOGLE_MAPS_API_KEY=your-maps-key
DATA_PATH=./data/astram_incidents.csv
BENGALURU_GRAPH_CACHE=./data/bengaluru.graphml
```

### Install

```bash
pip install fastapi uvicorn sqlalchemy asyncpg pydantic \
    pandas numpy lightgbm scikit-learn optuna joblib \
    redis googlemaps pulp networkx osmnx google-genai
```

### Run

```bash
uvicorn main:app --reload --port 8000
```

On first boot, the Data Foundation module loads the CSV and computes all derived statistics automatically. Train the forecasting models once data is loaded:

```bash
curl -X POST http://localhost:8000/api/forecast/train
```

Then connect the dashboard to `ws://localhost:8000/api/ws/dashboard` for live alerts.

## Example: forecasting an event

```bash
curl -X POST http://localhost:8000/api/forecast/predict \
  -H "Content-Type: application/json" \
  -d '{
    "event_cause": "public_event",
    "corridor": "Mysore Road",
    "start_datetime": "2026-06-26T18:00:00"
  }'
```

This returns the predicted priority, road-closure probability, corridor risk score, and an overall `risk_level` (Low/Medium/High/Critical) — the same context the AI Copilot and Compound Conflict Detector build on.

## Demo / hackathon notes

- The Surge Detector and Learning Engine include `is_demo_mode` flags that simulate realistic incident spikes and Google Maps congestion data when live feeds aren't available, with a one-shot guard so the autonomous scheduler doesn't spam the dashboard with repeat alerts during a live demo.
- The Learning Engine's autonomous scan and Surge Detector's polling daemon are designed to be wired into a scheduler (e.g. APScheduler) at app startup; that wiring lives in the main application entry point, outside this module set.
- All AI-generated content (Operational Orders, OSINT extraction, CCTV schema translation) is currently model `gemini-1.5-flash` and can be swapped via `ai_copilot/service.py`.

## License

Add your license of choice here.
