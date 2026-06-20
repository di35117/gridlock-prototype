"""
BTP Event Intelligence Platform — FastAPI entry point.
Boots the data foundation, trains the ML forecaster, and exposes all operational endpoints.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("main")

from database import init_db
from modules.data_foundation import service as data_foundation_service
from modules.data_foundation.router import router as data_foundation_router
from modules.impact_forecaster import trainer as forecaster_trainer
from modules.impact_forecaster import service as forecaster_service  # NEW IMPORT
from modules.impact_forecaster.router import router as impact_forecaster_router
from modules.compound_conflict.router import router as compound_conflict_router
from modules.ai_copilot.router import router as ai_copilot_router
from modules.surge_detector.router import router as surge_detector_router
from modules.surge_detector.service import run_autonomous_surge_scan
from modules.resource_recommender.router import router as resource_recommender_router
from modules.learning_engine.router import router as learning_engine_router
from modules.learning_engine.service import autonomous_event_learning_scan
from modules.routing_engine.router import router as routing_engine_router
from modules.osint_harvester.router import router as osint_harvester_router
from modules.websockets.router import router as websocket_router 
from modules.cctv_ingestion.router import router as cctv_ingestion_router

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━━━ BTP Event Intelligence — starting up ━━━")
    await init_db()
    logger.info("Database tables ready")
    
    df_status = await data_foundation_service.initialize_data_foundation()
    logger.info(f"Data foundation: {df_status}")
    
    if not forecaster_trainer.models_exist():
        logger.info("No trained forecaster models found — training now …")
        metrics = await forecaster_trainer.train_and_save()
        
        # FIX: Load models into memory immediately to prevent cold-start crashes
        forecaster_service.reload_models()
        
        logger.info(f"Impact Forecaster trained: {metrics}")
    else:
        logger.info("Impact Forecaster models already trained — skipping.")
        
    # Start Autonomous Monitoring Daemons
    scheduler.add_job(run_autonomous_surge_scan, 'interval', minutes=5)
    scheduler.add_job(autonomous_event_learning_scan, 'interval', minutes=5)
    scheduler.start()
    logger.info("Autonomous Monitoring Daemon (APScheduler) started.")
        
    logger.info("━━━ Startup complete — ready to serve ━━━")
    yield
    
    logger.info("━━━ Shutting down ━━━")
    scheduler.shutdown()

app = FastAPI(title="BTP Event Intelligence Platform", lifespan=lifespan)

# CORS opened for seamless frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registering all built modules
app.include_router(data_foundation_router)
app.include_router(impact_forecaster_router)
app.include_router(compound_conflict_router)
app.include_router(surge_detector_router)
app.include_router(resource_recommender_router)
app.include_router(routing_engine_router)
app.include_router(learning_engine_router)
app.include_router(ai_copilot_router)
app.include_router(osint_harvester_router)
app.include_router(websocket_router) 
app.include_router(cctv_ingestion_router)