"""
API routes for the AI Copilot.
"""
from fastapi import APIRouter, BackgroundTasks
from modules.ai_copilot import service
from modules.ai_copilot.models import CopilotRequest, CopilotResponse
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])

# A temporary in-memory dictionary to store our finished reports.
# (In production, this is where we would use the Redis container you have in docker-compose!)
_TASK_STORE = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

async def background_generate_order(task_id: str, request: CopilotRequest):
    """The background worker function that talks to Gemini."""
    try:
        # Run the heavy 5-second LLM task
        order_text = await service.generate_operational_order(
            event_cause=request.event_cause,
            corridor=request.corridor,
            expected_crowd=request.expected_crowd,
            event_details=request.event_details,
            event_datetime=request.event_datetime
        )
        # Save the result
        _TASK_STORE[task_id] = {"status": "completed", "data": order_text}
    except Exception as e:
        _TASK_STORE[task_id] = {"status": "failed", "error": str(e)}

@router.post("/generate", response_model=TaskResponse)
async def generate(request: CopilotRequest, background_tasks: BackgroundTasks):
    """Instantly accepts the request and pushes the heavy work to the background."""
    # 1. Generate a unique tracking ticket
    task_id = str(uuid.uuid4())
    
    # 2. Set initial status
    _TASK_STORE[task_id] = {"status": "processing"}
    
    # 3. Hand the heavy lifting to FastAPI's background worker
    background_tasks.add_task(background_generate_order, task_id, request)
    
    # 4. Return immediately (takes 0.01 seconds!)
    return TaskResponse(
        task_id=task_id, 
        status="processing", 
        message="Threat analysis and LLM generation started in the background."
    )

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Endpoint for the frontend dashboard to check if the report is ready."""
    task = _TASK_STORE.get(task_id)
    if not task:
        return {"status": "not_found", "message": "Invalid Task ID"}
    
    if task["status"] == "completed":
        return {"status": "completed", "operational_order": task["data"]}
    
    return {"status": task["status"]}