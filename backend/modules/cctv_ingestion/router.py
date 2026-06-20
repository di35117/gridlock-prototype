from fastapi import APIRouter, Request
from modules.cctv_ingestion.models import CCTVResponse
from modules.cctv_ingestion.tasks import process_cctv_task  # <-- Import the Celery task
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cctv", tags=["CCTV Integration Hub"])

@router.post("/webhook", response_model=CCTVResponse)
async def cctv_webhook(request: Request):  # <-- Removed background_tasks from signature
    """
    Universal Plug-and-Play Webhook for CCTV Vision models.
    Accepts valid JSON dictionaries and hands them off to the Celery/Redis queue.
    """
    # Accept incoming JSON payload
    raw_payload = await request.json()
    
    logger.info("Incoming CCTV vision payload detected. Routing to Celery queue...")
    
    # Dispatch to the distributed Celery worker queue instantly
    process_cctv_task.delay(raw_payload)
    
    return CCTVResponse(
        status="Accepted", 
        message="CCTV payload safely queued in Redis broker. Autonomous processing initialized."
    )