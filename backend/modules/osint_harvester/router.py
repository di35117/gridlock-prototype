from fastapi import APIRouter, BackgroundTasks
from modules.osint_harvester import service
from modules.osint_harvester.models import OSINTRequest, OSINTResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/osint", tags=["OSINT Harvester"])

@router.post("/process", response_model=OSINTResponse)
async def process_intel(request: OSINTRequest):
    result = await service.process_osint_intel(raw_text=request.raw_text, source=request.source)
    return OSINTResponse(**result)

@router.post("/webhook")
async def receive_social_webhook(request: OSINTRequest, background_tasks: BackgroundTasks):
    """
    Receives automated push payloads from enterprise social listening tools (e.g., Dataminr).
    Processes the intelligence autonomously in the background.
    """
    logger.info(f"Incoming automated webhook detected from source: {request.source}")
    
    # Send the LLM extraction and Geocoding to a background thread
    background_tasks.add_task(service.process_osint_intel, raw_text=request.raw_text, source=request.source)
    
    return {"status": "Accepted", "message": "Webhook received. Autonomous OSINT processing initiated."}