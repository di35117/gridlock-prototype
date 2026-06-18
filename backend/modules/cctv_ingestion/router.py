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
    Accepts ANY arbitrary JSON structure. Normalizes it dynamically via LLM if needed.
    """
    # Accept literally any JSON dictionary format without crashing
    raw_payload = await request.json()
    
    logger.info("Incoming CCTV vision payload detected. Routing to translation layer...")
    
    # Process in the background so the CCTV camera gets an instant 200 OK
    background_tasks.add_task(service.process_cctv_payload, raw_payload)
    
    return CCTVResponse(
        status="Accepted", 
        message="CCTV payload received for dynamic normalization."
    )