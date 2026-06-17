"""
BTP Event Intelligence Platform — FastAPI entry point.
Boots the data foundation (CSV → DB) and trains the impact forecaster
(if not already trained) on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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
from modules.impact_forecaster.router import router as impact_forecaster_router
from modules.compound_conflict.router import router as compound_conflict_router
from modules.ai_copilot.router import router as ai_copilot_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━━━ BTP Event Intelligence — starting up ━━━")

    await init_db()
    logger.info("Database tables ready")

    df_result = await data_foundation_service.initialize_data_foundation()
    logger.info(f"Data foundation: {df_result}")

    if not forecaster_trainer.models_exist():
        logger.info("No trained forecaster models found — training now …")
        metrics = await forecaster_trainer.train_and_save()
        logger.info(f"Impact Forecaster trained: {metrics}")
    else:
        logger.info("Impact Forecaster models already trained — skipping.")

    logger.info("━━━ Startup complete — ready to serve ━━━")
    yield
    logger.info("━━━ Shutting down ━━━")


app = FastAPI(title="BTP Event Intelligence Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_foundation_router)
app.include_router(impact_forecaster_router)
app.include_router(compound_conflict_router)
app.include_router(ai_copilot_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "BTP Event Intelligence"}