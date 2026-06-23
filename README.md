# Gridlock

![Flipkart Gridlock 2.0](https://img.shields.io/badge/Hackathon-Flipkart%20Gridlock%202.0-FFE11B?style=flat-square&labelColor=2874F0)
![Bengaluru Traffic Police](https://img.shields.io/badge/Built%20for-Bengaluru%20Traffic%20Police-0033A0?style=flat-square&labelColor=111827)
![MapmyIndia](https://img.shields.io/badge/Geocoding%20%26%20Live%20Traffic-MapmyIndia-FF5722?style=flat-square&labelColor=111827)

An autonomous, predictive command platform for the Bengaluru Traffic Police (BTP).

Gridlock takes 8,173+ historical ASTRAM traffic incident records and turns them into a live decision-support system. It forecasts how a planned event will hit a road corridor before it happens, catches the moment construction work and a new event start compounding into serious risk, pulls in intel from CCTV feeds and social/news sources on its own, recommends manpower and barricade placement, works out diversion routes around blockages, and learns from what actually happened afterward so the forecasts get sharper over time. All of it streams live to a command-center dashboard over WebSockets.

It's built as a modular FastAPI backend, so each capability (forecasting, routing, OSINT, learning, and so on) lives as its own swappable module on top of a shared data layer.

## The problem

BTP currently manages traffic operations reactively. There's no system that can answer, ahead of time: if we approve this procession on Mysore Road at 6 PM on a Friday, how bad will it actually get, which station should respond, and is there already a construction zone nearby that's going to make it worse? This is the gap Problem Statement 2 calls out directly, and it's the one Gridlock closes — combining a trained ML risk model, rule-based compound-risk math, an optimizer, and an LLM copilot into one pipeline.

## Core capabilities

| Module | What it does |
|---|---|
| **Data Foundation** | Loads and cleans the ASTRAM incident CSV into PostgreSQL on first boot. Computes per-corridor risk DNA, station-corridor mappings, and per-event-cause statistics that every other module reads from. |
| **Impact Forecaster** | Two LightGBM classifiers (priority and road-closure), tuned with Optuna, trained on cyclic time, geography, vehicle-type, and historical corridor/cause features. Outputs a blended `compound_risk_score` and a risk tier for any event before it happens. |
| **Compound Conflict Detector** | Catches when active construction zones on a corridor multiply the risk of a new event, capped at a 2.5x multiplier, and raises explicit warnings (e.g. "diversion routing is mandatory"). |
| **AI Copilot** | Aggregates output from the Impact Forecaster, Compound Conflict Detector, Routing Engine, and Resource Recommender, then calls Gemini to draft a structured, field-ready Operational Order: threat assessment, station deployment, barricading & diversion strategy, action checklist. |
| **OSINT Harvester** | Takes raw, unstructured text (news, social media, radio), including via webhook from enterprise listening tools, and uses Gemini as a named-entity extractor to turn it into a structured event. Geocodes the location via MapmyIndia, forecasts its risk, and broadcasts an alert on its own. |
| **CCTV Ingestion** | A plug-and-play webhook for third-party computer-vision camera systems. Incoming payloads are offloaded to a Celery/Redis task queue so high alert volume never blocks the main event loop. Matches a known schema instantly, or falls back to a Gemini-powered "universal data translator" for proprietary payloads, then feeds the result into the forecaster. |
| **Surge Detector** | Z-score anomaly detection against each corridor's historical hourly baseline. Flags sudden incident spikes (above 2σ) for immediate QR (Quick Response) team deployment. Runs as a background polling daemon too. |
| **Resource Recommender** | Recommends primary/backup stations and a manpower tier per risk level. Uses linear programming (PuLP) to optimally split a limited officer pool across multiple simultaneous events by risk-weighted priority. |
| **Tactical Routing Engine** | Loads a Bengaluru road network graph (OSMnx/NetworkX) from a pre-compiled binary pickle cache for sub-second startup, removes nodes/edges near active construction, and computes a diversion route plus barricade placement points as GeoJSON — with a forced-path fallback if no safe detour exists. |
| **Learning Engine** | Registers events in Redis as they're created. Once an event wraps up, it autonomously polls the MapmyIndia Distance Matrix / Distance Matrix ETA APIs for live congestion ground-truth and runs an exponential-moving-average correction against the original forecast, so the model's calibration improves over time without retraining. |
| **WebSockets** | A connection manager that broadcasts every alert (surge, OSINT, CCTV) instantly to all connected dashboard clients. |

## Architecture

```
┌─────────────┐   ┌──────────────┐
│ CCTV Webhook│   │ OSINT Webhook│      (autonomous intake)
└──────┬──────┘   └──────┬───────┘
       │  raw JSON        │  raw text
       ▼                  ▼
  Celery + Redis     Gemini NER
  task queue          extraction
  (non-blocking)          │
       │                  │
       ▼                  │
  Gemini schema           │
  normalization           │
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
   (PuLP optimizer)    (OSMnx/NetworkX,
                        binary pickle cache)
        │                  │
        └────────┬─────────┘
                 ▼
   FastAPI REST (/api/*)  +  WebSocket (/api/ws/dashboard)
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Frontend — React 19 + Vite                  │
│                                               │
│  zustand           live alert feed, UI state │
│  maplibre-gl /      keyless vector map        │
│  react-map-gl       (CartoDB tiles) — risk    │
│                      overlays, diversion      │
│                      routes, barricades       │
│  @turf/turf         geo math on the GeoJSON   │
│                      from the Routing Engine  │
│  react-markdown     renders the Copilot's     │
│                      Operational Orders       │
│  lucide-react       icon set                  │
└─────────────────────────────────────────────┘
                 │
                 ▼
        Learning Engine (Redis EMA)
        polls MapmyIndia Distance Matrix,
        runs on its own background loop,
        closes the loop on event end
```

MapmyIndia is confirmed used **server-side only** — for Geocoding (OSINT Harvester) and Distance Matrix ground-truth (Learning Engine), both verified directly against the actual service code. The diagram above shows the live map rendering on **MapLibre GL JS** against open CartoDB tiles instead of MapmyIndia's Web SDK, per the documented rationale (the original SDK integration was fragile across preview/production domains, with frequent `401`s tied to per-domain whitelisting). **This specific part hasn't been independently confirmed against the actual frontend code** — every `BengaluruMap.jsx` reviewed so far still imports and initializes `mappls` directly, not MapLibre. If the migration is done, this section is accurate; if it's still planned, treat this diagram as the target architecture and double check `BengaluruMap.jsx` before assuming the frontend needs no map key.

The frontend pulls data over REST for one-off requests (forecasts, tactical plans, diversion routes, copilot orders) and stays subscribed to the WebSocket for push alerts (surge, OSINT, CCTV) without polling. The Learning Engine isn't driven by the frontend at all; it runs on its own schedule in the background and feeds corrected calibration back into future forecasts.

Every feature module reads shared, pre-computed corridor/event statistics from the Data Foundation layer instead of re-scanning raw incident data on every request.

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI (async), Pydantic v2 |
| Database | PostgreSQL + PostGIS via SQLAlchemy (async) and asyncpg |
| Cache / state / broker | Redis (async client) — Learning Engine calibration memory, WebSocket pub/sub, and the Celery broker |
| Background tasks | Celery — offloads high-volume CCTV webhook payloads off the main event loop |
| Machine learning | LightGBM, scikit-learn, Optuna (Bayesian hyperparameter tuning), pandas/numpy |
| Generative AI | Google Gemini (`google-genai` SDK) for copilot drafting, schema translation, and NER extraction |
| Optimization | PuLP (CBC solver) for linear-programming manpower allocation |
| Routing | OSMnx and NetworkX over a Bengaluru road graph, cached as a binary pickle for fast in-memory loading |
| Live traffic ground-truth | MapmyIndia Distance Matrix / Distance Matrix ETA APIs |
| Geocoding | MapmyIndia Geocoding API (OSINT Harvester) |
| Real-time transport | Native FastAPI WebSockets |
| Frontend | React 19, Vite, Tailwind CSS 4, MapLibre GL JS (keyless, CartoDB tiles), Zustand |

## Project structure

```
gridlock-prototype/
├── backend/
│   ├── tasks.py                  # Celery app + worker tasks (CCTV ingestion offload)
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
- PostgreSQL (with PostGIS)
- Redis (also doubles as the Celery broker)
- A Gemini API key
- A MapmyIndia REST/Map SDK key plus an OAuth client ID/secret — used server-side only, for Geocoding and Distance Matrix. Falls back to a fixed fallback coordinate and simulated congestion data in demo mode if unavailable.
- The ASTRAM incident CSV and a pre-compiled Bengaluru road graph (binary pickle) for the routing engine

### Environment variables

This project's `.env` has shifted a few times during the build — below is the most complete picture, merged from `config.py` and the local setup script. Treat it as a strong starting point and reconcile it against your actual `config.py` before deploying, since a couple of these have moved or been renamed along the way.

```
DATABASE_URL=postgresql+asyncpg://btp_admin:btp_secure_pass@localhost:5432/btp_intelligence
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key_here

# MapmyIndia — used server-side only (Geocoding + Distance Matrix), never on the frontend
MAPMYINDIA_STATIC_KEY=your_mapmyindia_rest_and_sdk_key
MAPMYINDIA_CLIENT_ID=your_mapmyindia_client_id
MAPMYINDIA_CLIENT_SECRET=your_mapmyindia_client_secret

# Security — generate via: openssl rand -hex 32
SECRET_KEY=your_secret_key_here

# Behavior flags
FRONTEND_URL=http://localhost:5173
DEMO_MODE=True

# File paths
DATA_PATH=data/astram_events.csv
BENGALURU_GRAPH_CACHE=data/bengaluru_graph.pkl
```

`GOOGLE_MAPS_API_KEY` doesn't need to be here anymore — the Learning Engine now polls MapmyIndia's Distance Matrix / Distance Matrix ETA APIs directly for ground-truth congestion instead of Google Maps.

### Install

```bash
pip install fastapi uvicorn sqlalchemy asyncpg pydantic \
    pandas numpy lightgbm scikit-learn optuna joblib \
    redis celery pulp networkx osmnx google-genai aiohttp
```

### Compiling the routing graph

Parsing the raw GraphML road network at startup spikes memory enough to OOM-kill a small container. Compile it once into a binary pickle instead:

```bash
python scripts/compile_network_graph.py
```

This writes `data/bengaluru_graph.pkl`, which the Routing Engine deserializes directly into memory at boot — under a second, instead of 30+.

### Run

This needs two backend processes running side by side: the API server, and the Celery worker that offloads CCTV webhook processing.

```bash
# Terminal 1 — API server
uvicorn main:app --reload --port 8000
```

```bash
# Terminal 2 — Celery worker
celery -A tasks.celery_app worker --loglevel=info --pool=solo
```

Double-check the variable name in `tasks.py` before running this — the documented Celery code instantiates it as `app = Celery("traffic_tasks", ...)`, which would make the correct command `celery -A tasks.app worker`, not `tasks.celery_app`. Use whichever name `tasks.py` actually defines.

`--pool=solo` is required on Windows, since Celery's default prefork pool relies on `fork()`, which isn't available there. On macOS/Linux you can drop it for better concurrency.

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
| `maplibre-gl`, `react-map-gl` | Interactive, keyless map rendering against public CartoDB tiles: corridors, risk overlays, diversion routes, barricade points |
| `@turf/turf` | Client-side geospatial calculations (distances, buffers) on top of the GeoJSON the Routing Engine returns |
| `zustand` | Lightweight global state backing the live WebSocket alert feed and dashboard UI state |
| `react-markdown` | Renders the AI Copilot's Markdown-formatted Operational Orders |
| `lucide-react` | Icon set |
| `eslint` + plugins | Linting (flat config, React Hooks / Refresh rules) |

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000
```

No commercial map API key is needed here **if** the MapLibre migration described in the architecture section is actually live in `BengaluruMap.jsx` — unconfirmed as of this writing, see the note above.

By default Vite serves on `http://localhost:5173`.

Other scripts:

```bash
npm run build     # production build
npm run preview   # preview the production build locally
npm run lint      # run ESLint
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

## Testing

| Layer | What it covers |
|---|---|
| **End-to-end** (`test_e2e.py`) | Full incident lifecycle — mocked OSINT webhook → Gemini extraction → Impact Forecaster → Compound Conflict → broadcast `CRITICAL_ALERT` → Routing Engine + Resource Recommender. |
| **Unit / service** | One file per module (`test_data_foundation.py`, `test_cctv.py`, `test_impact.py`, `test_compound.py`, `test_copilot.py`, `test_learning.py`, `test_websocket.py`) — covers feature engineering, the Celery handoff, LightGBM thresholding, the 2.5x compound-risk cap, Copilot Markdown formatting, EMA calibration, and WebSocket connection cleanup. |
| **Database integration** (`test_db_integration.py`, `conftest.py`) | Spins up an ephemeral PostgreSQL 15 instance per test session via **Testcontainers**, so the Surge Detector's Z-score SQL and other spatial queries run against the real PostgreSQL dialect instead of a SQLite mock. |
| **Load testing** (`locustfile.py`) | Simulates concurrent traffic against the CCTV webhook, Surge Detector polling, and OSINT firehose via **Locust**, to catch event-loop starvation or connection-pool exhaustion before it happens live. |

CI runs the same Testcontainers-backed PostgreSQL instance inside GitHub Actions on every pull request, then tears it down automatically — no test data ever touches the real database.

## Deployment

| Tier | Platform | Notes |
|---|---|---|
| Frontend | Vercel Edge Network | Static Vite build, served from the nearest edge node. No commercial map API key needed, since the map runs on MapLibre/CartoDB. |
| Backend (API + Celery workers) | Containerized (Railway / AWS ECS) | Stateless ASGI pods behind a load balancer; Celery workers run as a separate process from the same image. |
| Data layer | Managed PostgreSQL 15 + Redis | Redis backs both the Celery broker and the WebSocket pub/sub fan-out. |

The routing graph is the one piece that doesn't fit a small container out of the box: parsing the raw 50MB GraphML file at startup spikes memory to roughly 1.5GB, enough to OOM-kill a 500MB container. Pre-compiling it locally into a binary pickle and deserializing that at boot instead drops both startup time (32s → under 0.4s) and memory footprint (1.5GB → ~150MB) enough to run comfortably on cheap container hardware.

## Demo / hackathon notes

Built by **Team Dark Sister** (Dishank Choudhury — team lead, Tanya Shahi) for **Flipkart Gridlock 2.0**.

The Surge Detector and Learning Engine include `is_demo_mode` flags that simulate realistic incident spikes and MapmyIndia congestion data when live feeds aren't available, with a one-shot guard so the autonomous scheduler doesn't spam the dashboard with repeat alerts during a live demo.

The Learning Engine's autonomous scan and Surge Detector's polling daemon run on an APScheduler instance wired up in the main application entry point.

All AI-generated content (Operational Orders, OSINT extraction, CCTV schema translation) currently runs on `gemini-3.5-flash` and can be swapped via `ai_copilot/service.py`. Worth a final check before the demo, though — internal notes reference both `gemini-3.5-flash` and `gemini-1.5-flash` for the Copilot specifically, so confirm which one is actually wired in rather than assuming.

## License

Add your license of choice here.