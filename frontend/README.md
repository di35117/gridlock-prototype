# Gridlock

An autonomous, predictive command platform for the Bengaluru Traffic Police (BTP).

Gridlock takes 8,173+ historical ASTRAM traffic incident records and turns them into a live decision-support system. It forecasts how a planned event will hit a road corridor before it happens, catches the moment construction work and a new event start compounding into serious risk, pulls in intel from CCTV feeds and social/news sources on its own, recommends manpower and barricade placement, works out diversion routes around blockages, and learns from what actually happened afterward so the forecasts get sharper over time. All of it streams live to a command-center dashboard over WebSockets.

It's built as a modular FastAPI backend, so each capability (forecasting, routing, OSINT, learning, and so on) lives as its own swappable module on top of a shared data layer.

## The problem

BTP currently manages traffic operations reactively. There's no system that can answer, ahead of time: if we approve this procession on Mysore Road at 6 PM on a Friday, how bad will it actually get, which station should respond, and is there already a construction zone nearby that's going to make it worse? Gridlock closes that gap by combining a trained ML risk model, rule-based compound-risk math, an optimizer, and an LLM copilot into one pipeline.

## Core capabilities

| Module | What it does |
|---|---|
| **Data Foundation** | Loads and cleans the ASTRAM incident CSV into PostgreSQL on first boot. Computes per-corridor risk DNA, station-corridor mappings, and per-event-cause statistics that every other module reads from. |
| **Impact Forecaster** | Two LightGBM classifiers (priority and road-closure), tuned with Optuna, trained on cyclic time, geography, vehicle-type, and historical corridor/cause features. Outputs a blended `compound_risk_score` and a risk tier for any event before it happens. |
| **Compound Conflict Detector** | Catches when active construction zones on a corridor multiply the risk of a new event, capped at a 2.5x multiplier, and raises explicit warnings (e.g. "diversion routing is mandatory"). |
| **AI Copilot** | Calls Gemini to pull context from the forecaster and conflict detector, then drafts a structured, field-ready Operational Order: threat assessment, station deployment, barricading strategy, action checklist. |
| **OSINT Harvester** | Takes raw, unstructured text (news, social media, radio), including via webhook from enterprise listening tools, and uses Gemini as a named-entity extractor to turn it into a structured event. Forecasts its risk and broadcasts an alert on its own. |
| **CCTV Ingestion** | A plug-and-play webhook for third-party computer-vision camera systems. Matches a known schema instantly, or falls back to a Gemini-powered "universal data translator" for proprietary payloads, then feeds the result into the forecaster. |
| **Surge Detector** | Z-score anomaly detection against each corridor's historical hourly baseline. Flags sudden incident spikes (above 2σ) for immediate QR (Quick Response) team deployment. Runs as a background polling daemon too. |
| **Resource Recommender** | Recommends primary/backup stations and a manpower tier per risk level. Uses linear programming (PuLP) to optimally split a limited officer pool across multiple simultaneous events by risk-weighted priority. |
| **Tactical Routing Engine** | Loads a Bengaluru road network graph (OSMnx/NetworkX), removes nodes near active construction, and computes a diversion route plus barricade placement points as GeoJSON for the map UI. |
| **Learning Engine** | Registers events in Redis as they're created. Once an event wraps up, it autonomously polls live Google Maps congestion data and runs an exponential-moving-average correction against the original forecast, so the model's calibration improves over time without retraining. |
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

Every feature module reads shared, pre-computed corridor/event statistics from the Data Foundation layer instead of re-scanning raw incident data on every request.

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI (async), Pydantic v2 |
| Database | PostgreSQL via SQLAlchemy (async) and asyncpg |
| Cache / state | Redis (async client), powers the Learning Engine's calibration memory |
| Machine learning | LightGBM, scikit-learn, Optuna (Bayesian hyperparameter tuning), pandas/numpy |
| Generative AI | Google Gemini (`google-genai` SDK) for copilot drafting, schema translation, and NER extraction |
| Optimization | PuLP (CBC solver) for linear-programming manpower allocation |
| Routing | OSMnx and NetworkX over a cached Bengaluru road graph |
| Live traffic data | Google Maps Distance Matrix API |
| Real-time transport | Native FastAPI WebSockets |
| Frontend | React 19, Vite, Tailwind CSS 4, MapLibre GL JS, Zustand |

## Project structure

```
gridlock-prototype/
├── backend/
│   └── modules/
│       ├── ai_copilot/           # Gemini-drafted operational orders
│       ├── cctv_ingestion/       # Autonomous CCTV webhook + LLM normalization
│       ├── compound_conflict/    # Construction × event risk multiplier
│       ├── data_foundation/      # CSV → PostgreSQL ETL, corridor/event stats
│       ├── impact_forecaster/    # LightGBM training + inference
│       ├── learning_engine/      # Redis-backed EMA self-calibration
│       ├── osint_harvester/      # Unstructured text → structured event pipeline
│       ├── resource_recommender/ # Station assignment + LP manpower optimizer
│       ├── routing_engine/       # Graph-based diversion routing
│       ├── surge_detector/       # Z-score anomaly detection
│       └── websockets/           # Connection manager + dashboard endpoint
└── frontend/                     # React 19 + Vite + MapLibre command-center dashboard
```

Each feature module follows the same pattern internally: `models.py` for Pydantic schemas, `router.py` for FastAPI routes, `service.py` for the actual logic, and an `__init__.py`. `impact_forecaster` also has a `trainer.py` for model training.

## API reference

All routes are mounted under `/api`. Replace `{corridor}` with a URL-encoded corridor name (e.g. `Mysore Road`).

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/data/status` | Row counts for each core table, used for dashboard boot state |
| `GET` | `/api/data/corridor-profiles` | All corridor risk profiles, sorted by risk |
| `GET` | `/api/data/corridor-profiles/{corridor}` | Single corridor profile |
| `GET` | `/api/data/event-stats` | Per-event-cause statistics |
| `GET` | `/api/data/station-mapping/{corridor}` | Police stations historically handling a corridor |
| `POST` | `/api/data/reload` | Force a full CSV reload (truncates incident data) |
| `GET` | `/api/forecast/status` | Whether trained models exist |
| `GET` | `/api/forecast/metrics` | Trained model performance metrics |
| `POST` | `/api/forecast/train` | Train/retrain the priority and closure classifiers |
| `POST` | `/api/forecast/predict` | Forecast an event's impact (priority, closure probability, risk tier) |
| `POST` | `/api/conflict/detect` | Compute compound risk from construction and event severity |
| `POST` | `/api/copilot/generate` | Generate a Gemini-drafted Operational Order |
| `POST` | `/api/osint/process` | Manually process raw OSINT text into a forecasted event |
| `POST` | `/api/osint/webhook` | Autonomous webhook for social-listening tools |
| `POST` | `/api/cctv/webhook` | Autonomous webhook for CCTV vision systems |
| `POST` | `/api/surge/check` | Z-score surge check against a corridor's hourly baseline |
| `POST` | `/api/recommend/tactical` | Station, manpower tier, and barricade count recommendation |
| `POST` | `/api/recommend/optimize` | LP-optimized officer allocation across multiple events |
| `POST` | `/api/routing/diversion` | Diversion route and barricade points avoiding construction |
| `POST` | `/api/learning/register` | Register an active event for post-event learning |
| `POST` | `/api/learning/feedback` | Manually trigger the EMA calibration update |
| `WS` | `/api/ws/dashboard` | Real-time alert stream for the frontend dashboard |

## Getting started

### Backend prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- A Gemini API key
- A Google Maps API key (optional, falls back to simulated congestion data in demo mode)
- The ASTRAM incident CSV and a pre-downloaded Bengaluru road graph for the routing engine

### Environment variables

This is the actual `.env.example` from the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here

# Geospatial & Mapping APIs
# Required for the Routing Engine and Google Maps validation steps
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Security
# Run 'openssl rand -hex 32' to generate a secure fallback secret key
SECRET_KEY=your_secret_key_here

# File Paths & Cache Configurations
# Path to the ASTRAM historical incident dataset (e.g., data/astram_events.csv)
DATA_PATH=data/astram_events.csv
# Path where the serialized OpenStreetMap graph network file is cached
BENGALURU_GRAPH_CACHE=data/bengaluru_graph.json

DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=60
USE_PGBOUNCER=FALSE
```

A couple of things worth double-checking against your actual `config.py` before deploying:

Database connection. The pooling vars above (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `USE_PGBOUNCER`) configure the SQLAlchemy engine, but the connection string itself (host, user, password, db name, or a single `DATABASE_URL`) isn't in this snippet. Make sure it's set somewhere `config.py` / `database.py` actually reads from.

Redis. `learning_engine/service.py` reads a `REDIS_URL` at import time to back its EMA calibration store, and it isn't listed here either. It probably lives in a separate `.env` entry or defaults to `redis://localhost:6379` in code, worth confirming so the Learning Engine doesn't fail silently on startup.

Also note `BENGALURU_GRAPH_CACHE` here points to a `.json` file, while `routing_engine/service.py` loads it via `ox.load_graphml(...)`, which expects GraphML (XML), not JSON. Either the extension in `.env.example` is just illustrative or the cache format needs to match what `load_graphml` can parse.

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

### Frontend

The dashboard is a React 19 + Vite single-page app.

| Package | Role |
|---|---|
| `react`, `react-dom` | UI runtime (v19) |
| `vite` | Dev server and build tool |
| `tailwindcss`, `@tailwindcss/vite` | Utility-first styling (Tailwind v4 Vite plugin) |
| `maplibre-gl`, `react-map-gl` | Interactive map rendering: corridors, risk overlays, diversion routes, barricade points |
| `@turf/turf` | Client-side geospatial calculations (distances, buffers) on top of the GeoJSON the Routing Engine returns |
| `zustand` | Lightweight global state, likely backing the live WebSocket alert feed and dashboard UI state |
| `react-markdown` | Renders the AI Copilot's Markdown-formatted Operational Orders |
| `lucide-react` | Icon set |
| `eslint` + plugins | Linting (flat config, React Hooks / Refresh rules) |

Install and run:

```bash
cd frontend
npm install
npm run dev
```

By default Vite serves on `http://localhost:5173`. Point the app at the backend by configuring the API base URL and WebSocket URL (`ws://localhost:8000/api/ws/dashboard`). Check `src/` for where these are defined (an `.env` file or a config constant), and add a `.env.example` if one doesn't exist yet since it wasn't included in the files shared so far.

Other scripts:

```bash
npm run build     # production build
npm run preview   # preview the production build locally
npm run lint       # run ESLint
```

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

This returns the predicted priority, road-closure probability, corridor risk score, and an overall `risk_level` (Low/Medium/High/Critical). It's the same context the AI Copilot and Compound Conflict Detector build on.

## Demo / hackathon notes

The Surge Detector and Learning Engine include `is_demo_mode` flags that simulate realistic incident spikes and Google Maps congestion data when live feeds aren't available, with a one-shot guard so the autonomous scheduler doesn't spam the dashboard with repeat alerts during a live demo.

The Learning Engine's autonomous scan and Surge Detector's polling daemon are meant to be wired into a scheduler (e.g. APScheduler) at app startup. That wiring lives in the main application entry point, outside this module set.

All AI-generated content (Operational Orders, OSINT extraction, CCTV schema translation) currently runs on `gemini-3.5-flash` and can be swapped via `ai_copilot/service.py`.

## License

Add your license of choice here.


