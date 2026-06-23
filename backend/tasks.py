"""
Distributed Task Queue Worker for Gridlock.
Maintains a single persistent event loop across tasks to prevent connection pool fragmentation.
Handles both CCTV Ingestion and AI Copilot Orchestration.
Configured for dynamic Cloud Deployment environments and robust data serialization.
"""
import os
import asyncio
import logging
from datetime import datetime
from celery import Celery

# Import your CCTV service
from modules.cctv_ingestion.service import process_cctv_payload

logger = logging.getLogger(__name__)

# 1. ENVIRONMENT CONFIGURATION: Dynamically pull your production Redis URL.
# If REDIS_URL is not found in the environment, it falls back to your local setup automatically.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "gridlock_tasks", 
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Network and resource optimizations for cloud deployments
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # Clear out completed task metadata from Redis after 1 hour to save memory
)

# Global tracker for the worker loop lifecycle
_WORKER_LOOP = None

def get_worker_event_loop():
    """
    Retrieves or establishes a single persistent event loop for the worker.
    Fixes the 'Event loop is closed' errors with global async resources like asyncpg.
    """
    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        try:
            _WORKER_LOOP = asyncio.get_event_loop()
        except RuntimeError:
            _WORKER_LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(_WORKER_LOOP)
    return _WORKER_LOOP

# ==========================================
# TASK 1: CCTV INGESTION
# ==========================================
@celery_app.task(name="tasks.process_cctv_task", rate_limit="15/m", max_retries=3, default_retry_delay=10)
def process_cctv_task(raw_payload: dict):
    """Executes ingestion using run_until_complete to keep connection states alive."""
    try:
        logger.info(f"[Worker] Processing enqueued CCTV task payload.")
        loop = get_worker_event_loop()
        
        # Safely execute the async CCTV processor
        return loop.run_until_complete(process_cctv_payload(raw_payload))
    except Exception as e:
        logger.error(f"Worker execution crash prevented for CCTV: {e}")
        return {"status": "failed", "error": str(e)}

# ==========================================
# TASK 2: AI COPILOT GENERATION
# ==========================================
@celery_app.task(name="tasks.generate_copilot_order", bind=True)
def generate_copilot_order_task(self, request_data: dict):
    """
    Celery task that orchestrates all Intelligence Modules safely in the background.
    """
    # CRITICAL FIX: Convert the incoming string format back into a robust datetime object
    # This prevents runtime attribute crashes when the down-stream modules look for .hour or .weekday()
    if isinstance(request_data.get("event_datetime"), str):
        try:
            request_data["event_datetime"] = datetime.fromisoformat(request_data["event_datetime"])
        except ValueError:
            logger.warning("[Worker] event_datetime was not in standard ISO format. Attempting parsing fallback...")
            request_data["event_datetime"] = datetime.strptime(request_data["event_datetime"], "%Y-%m-%d %H:%M:%S")

    loop = get_worker_event_loop()
    
    async def run_intelligence_pipeline():
        # Import inside the function to prevent circular dependency issues at boot time
        from modules.ai_copilot import service as copilot_service
        from modules.routing_engine.service import calculate_tactical_diversion
        from modules.resource_recommender.service import optimize_manpower
        from modules.compound_conflict.service import detect_conflict

        logger.info(f"[Worker] Starting AI Copilot analysis for corridor: {request_data.get('corridor')}")

        # 1. Generate the LLM Text Operational Report via Gemini
        order_text = await copilot_service.generate_operational_order(
            event_cause=request_data["event_cause"],
            corridor=request_data["corridor"],
            expected_crowd=request_data["expected_crowd"],
            event_details=request_data["event_details"],
            event_datetime=request_data["event_datetime"]
        )

        # 2. Conflict Detection
        has_construction = False
        compound_multiplier = 1.0
        try:
            conflict_data = await detect_conflict(request_data["corridor"], request_data["event_cause"])
            has_construction = conflict_data.get("has_construction", False)
            compound_multiplier = conflict_data.get("compound_multiplier", 1.0)
        except Exception as e:
            logger.warning(f"Conflict detection failed: {e}")

        # 3. Routing (Only if risk is high or construction is present)
        diversion_routes, plotted_barricades = None, []
        if request_data.get("road_closure_prob", 0) > 0.6 or has_construction:
            try:
                route_res = await calculate_tactical_diversion(request_data["corridor"])
                diversion_routes = route_res.get("geojson")
                plotted_barricades = route_res.get("barricades", [])
            except Exception as e:
                logger.warning(f"Routing failed: {e}")

        # 4. Resource Allocation
        resources_payload = None
        try:
            resources_payload = await optimize_manpower(
                request_data["corridor"], 
                request_data["expected_crowd"]
            )
        except Exception as e:
            logger.warning(f"Resource optimization failed: {e}")

        # Return the final compiled dictionary (Celery saves this into Redis)
        return {
            "status": "completed",
            "operational_order": order_text,
            "barricades": plotted_barricades,
            "diversion_routes": diversion_routes,
            "resources": resources_payload,
            "compound_threats": {
                "has_construction": has_construction,
                "multiplier": compound_multiplier
            }
        }

    try:
        # Execute the pipeline in our safe event loop
        return loop.run_until_complete(run_intelligence_pipeline())
    except Exception as e:
        logger.error(f"Copilot background task failed: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise e