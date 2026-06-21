from fastapi import APIRouter, BackgroundTasks
from modules.ai_copilot import service
from modules.ai_copilot.models import CopilotRequest, CopilotResponse
from pydantic import BaseModel
import uuid
import logging
from modules.routing_engine.service import _get_construction_coordinates

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])
logger = logging.getLogger(__name__)

# A temporary in-memory dictionary to store our finished reports.
_TASK_STORE = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

async def background_generate_order(task_id: str, request: CopilotRequest):
    """The background worker function that talks to Gemini and the Routing Engine."""
    try:
        # 1. Generate the LLM Text
        order_text = await service.generate_operational_order(
            event_cause=request.event_cause,
            corridor=request.corridor,
            expected_crowd=request.expected_crowd,
            event_details=request.event_details,
            event_datetime=request.event_datetime
        )
        
        # 2. Wire in the Routing Engine! Get real construction choke points
        construction_coords = await _get_construction_coordinates(request.corridor)
        
        # 3. CRITICAL: React MapLibre expects [[longitude, latitude]], NOT {"lat": x, "lon": y}
        formatted_barricades = []
        for lat, lon in construction_coords:
            formatted_barricades.append([float(lon), float(lat)])

        # 4. Save the FULL payload to the task store
        _TASK_STORE[task_id] = {
            "status": "completed", 
            "operational_order": order_text,
            "barricades": formatted_barricades,
            "diversion_routes": None, # Will be drawn by React if left null
            "resources": None
        }
    except Exception as e:
        logger.error(f"Copilot background task failed: {e}")
        _TASK_STORE[task_id] = {"status": "failed", "error": str(e)}

@router.post("/generate", response_model=TaskResponse)
async def generate(request: CopilotRequest, background_tasks: BackgroundTasks):
    """Instantly accepts the request and pushes the heavy work to the background."""
    task_id = str(uuid.uuid4())
    _TASK_STORE[task_id] = {"status": "processing"}
    
    background_tasks.add_task(background_generate_order, task_id, request)
    
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
        return {"status": "failed", "error": "Task not found"}
        
    if task["status"] == "completed":
        # CRITICAL FIX: We are now returning the FULL payload to React!
        return {
            "status": "completed", 
            "operational_order": task["operational_order"],
            "barricades": task["barricades"],
            "diversion_routes": task["diversion_routes"],
            "resources": task["resources"]
        }
        
    return {"status": task["status"]}