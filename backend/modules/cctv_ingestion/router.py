# backend/modules/cctv_ingestion/router.py
from fastapi import APIRouter, Request
import logging

# Import the centralized Celery application from the root directory
from tasks import celery_app

router = APIRouter(prefix="/api/cctv", tags=["CCTV Ingestion"])
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def receive_cctv_webhook(request: Request):
    """
    Receives raw JSON telemetry from distributed CCTV nodes and instantly
    dispatches it to the centralized Celery task queue, returning a 202 status.
    """
    try:
        raw_payload = await request.json()
        
        # Enqueue the task to the central worker queue matching the decorator name in root tasks.py
        celery_app.send_task("tasks.process_cctv_task", args=[raw_payload])
        
        logger.info("[CCTV Router] Successfully dispatched raw payload to Celery queue.")
        return {"status": "accepted", "message": "CCTV payload queued for autonomous processing."}
        
    except Exception as e:
        logger.error(f"[CCTV Router] Failed to queue incoming webhook: {e}")
        return {"status": "error", "message": "Failed to accept payload or malformed JSON syntax."}