import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from modules.data_foundation.service import initialize_data_foundation
from modules.data_foundation.router import router as data_router

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / shutdown ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━━━ BTP Event Intelligence — starting up ━━━")

    # 1. Create all tables (if they don't exist)
    await init_db()
    logger.info("Database tables ready")

    # 2. Load ASTRAM data + compute profiles (skips if already loaded)
    result = await initialize_data_foundation()
    logger.info(f"Data foundation: {result}")

    logger.info("━━━ Startup complete — ready to serve ━━━")
    yield
    logger.info("━━━ Shutting down ━━━")


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="BTP Event Intelligence Platform",
    version="1.0.0",
    description=(
        "Compound conflict detection, event impact forecasting, "
        "resource recommendations, surge detection, and autonomous "
        "post-event learning for Bengaluru Traffic Police."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(data_router)

# More routers will be added here as modules are built:
# app.include_router(forecast_router)
# app.include_router(conflict_router)
# app.include_router(recommend_router)
# app.include_router(surge_router)
# app.include_router(copilot_router)
# app.include_router(learning_router)


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status":  "ok",
        "service": "BTP Event Intelligence Platform",
        "version": "1.0.0",
    }