# backend/modules/ai_copilot/router.py
import uuid
import logging
from fastapi import APIRouter
from celery.result import AsyncResult

# Import your models and central celery application
from modules.ai_copilot.models import CopilotRequest, TaskResponse
from tasks import celery_app

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=TaskResponse)
async def generate(request: CopilotRequest):
    """
    Accepts tactical demand configurations from the UI and safely dispatches
    the intelligence workflow pipeline to the distributed Celery/Redis workers.
    """
    # CRITICAL FIX: Convert datetime objects to ISO strings so they are fully JSON serializable by Celery
    serializable_payload = {
        "event_cause": request.event_cause,
        "corridor": request.corridor,
        "expected_crowd": request.expected_crowd,
        "event_details": request.event_details,
        "event_datetime": request.event_datetime.isoformat(),
        "latitude": request.latitude,
        "longitude": request.longitude
    }
    
    # Generate a stable UUID to identify the background operation
    task_id = str(uuid.uuid4())
    
    try:
        # Trigger the task on our global worker cluster using the explicit decorator name
        celery_app.send_task(
            "tasks.generate_copilot_order", 
            args=[serializable_payload], 
            task_id=task_id
        )
        
        logger.info(f"[Copilot Router] Successfully offloaded Task {task_id} to Redis broker cluster.")
        return TaskResponse(task_id=task_id, status="processing", message="Distributed threat analysis started.")
        
    except Exception as e:
        logger.error(f"[Copilot Router] Task enqueue failure: {e}")
        return TaskResponse(task_id=task_id, status="failed", message="Could not connect to background queue broker.")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Polls the production Redis result backend to securely fetch tactical data
    compiled by background worker containers.
    """
    # Connect directly to the Celery result cache for this specific task
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state == "SUCCESS":
        # Returns the full dict containing: operational_order, barricades, diversion_routes, resources, etc.
        return result.result
        
    elif result.state == "FAILURE":
        logger.error(f"[Copilot Router] Background worker task {task_id} failed runtime execution.")
        return {"status": "failed", "error": str(result.info)}
        
    elif result.state == "RETRY":
        return {"status": "processing", "message": "Task hit a minor threshold wall; currently retrying..."}
        
    else:
        # Catch-all states for PENDING / RECEIVED / STARTED
        return {"status": "processing"}