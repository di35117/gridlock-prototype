from fastapi import APIRouter, BackgroundTasks, Request
from modules.cctv_ingestion import service
from modules.cctv_ingestion.models import CCTVResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cctv", tags=["CCTV Integration Hub"])

@router.post("/webhook", response_model=CCTVResponse)
async def cctv_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Universal Plug-and-Play Webhook for CCTV Vision models.
    Accepts valid JSON dictionaries. Arrays/Strings are safely rejected in the background.
    Normalizes proprietary schema dynamically via LLM if needed.
    """
    # Accept incoming JSON payload
    raw_payload = await request.json()
    
    logger.info("Incoming CCTV vision payload detected. Routing to translation layer...")
    
    # BUG FIX 3 (Architecture): Process in the background so the CCTV camera gets an instant 200 OK
    # Non-dictionary payloads will be safely caught and logged by the service layer.
    background_tasks.add_task(service.process_cctv_payload, raw_payload)
    
    return CCTVResponse(
        status="Accepted", 
        message="CCTV payload received. Autonomous ingestion initiated."
    )