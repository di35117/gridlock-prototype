import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from database import init_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from modules.cctv_ingestion.router import router as cctv_router
from modules.osint_harvester.router import router as osint_router
from modules.surge_detector.router import router as surge_router
from modules.impact_forecaster.router import router as forecast_router
from modules.compound_conflict.router import router as conflict_router
from modules.resource_recommender.router import router as resource_router
from modules.routing_engine.router import router as routing_router
from modules.ai_copilot.router import router as copilot_router
from modules.learning_engine.router import router as learning_router
from modules.websockets.router import router as ws_router

from modules.learning_engine.service import autonomous_event_learning_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database
    logger.info("Initializing PostgreSQL Database...")
    await init_db()
    
    # 2. Start the Autonomous MLOps Learning Engine
    # Changed to 15 seconds for live demo impact
    scheduler.add_job(
        autonomous_event_learning_scan,
        trigger=IntervalTrigger(seconds=15),
        id="learning_engine_daemon",
        name="Scans for concluded events and calculates model drift",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Started Background Learning Engine Daemon (15s interval).")
    
    yield
    
    scheduler.shutdown()
    logger.info("Shutting down operations.")

app = FastAPI(title="BTP Event Intelligence Platform", version="1.0.0", lifespan=lifespan)

# --- NEW: Global GZip Compression ---
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Module Routers
app.include_router(cctv_router, prefix="/api/cctv", tags=["CCTV Ingestion"])
app.include_router(osint_router, prefix="/api/osint", tags=["OSINT Harvester"])
app.include_router(surge_router, prefix="/api/surge", tags=["Surge Detector"])
app.include_router(forecast_router, prefix="/api/forecast", tags=["Impact Forecaster"])
app.include_router(conflict_router, prefix="/api/conflict", tags=["Compound Conflict"])
app.include_router(resource_router, prefix="/api/resource", tags=["Resource Recommender"])
app.include_router(routing_router, prefix="/api/routing", tags=["Routing Engine"])
app.include_router(copilot_router, prefix="/api/copilot", tags=["AI Copilot"])
app.include_router(learning_router, prefix="/api/learning", tags=["Learning Engine"])
app.include_router(ws_router, prefix="/api/ws", tags=["WebSockets"])

@app.get("/")
def read_root():
    return {"status": "BTP Command Center Backend Active"}