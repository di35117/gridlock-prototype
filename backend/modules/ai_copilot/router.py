from fastapi import APIRouter, BackgroundTasks
from modules.ai_copilot import service as copilot_service
from modules.ai_copilot.models import CopilotRequest, TaskResponse
import uuid
import logging

# IMPORT YOUR REAL MATH & OPERATIONS RESEARCH MODULES!
from modules.routing_engine.service import calculate_tactical_diversion, _get_construction_coordinates
from modules.resource_recommender.service import optimize_manpower
from modules.compound_conflict.service import detect_conflict

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])
logger = logging.getLogger(__name__)

_TASK_STORE = {}

async def background_generate_order(task_id: str, request: CopilotRequest):
    """Orchestrates all 4 backend intelligence modules to serve the UI."""
    try:
        # 1. Generate the LLM Text Operational Report via Gemini
        order_text = await copilot_service.generate_operational_order(
            event_cause=request.event_cause,
            corridor=request.corridor,
            expected_crowd=request.expected_crowd,
            event_details=request.event_details,
            event_datetime=request.event_datetime
        )
        
        # 2. Get Real Infrastructure Conflicts (Compound Conflict Module)
        has_construction = False
        compound_multiplier = 1.0
        try:
            lat = getattr(request, 'latitude', 12.9716)
            lon = getattr(request, 'longitude', 77.5946)
            
            # FIX: Passing exactly 2 arguments (assuming your function takes lat, lon)
            # If your function expects (corridor, radius), change to: detect_conflict(request.corridor, 100)
            conflict_data = await detect_conflict(lat, lon) 
            
            if isinstance(conflict_data, dict):
                has_construction = conflict_data.get("construction_incident_count", 0) > 0
                compound_multiplier = conflict_data.get("compound_multiplier", 1.0)
        except Exception as e:
            logger.error(f"Compound conflict check failed (using defaults): {e}")
        
        # 3. Operations Research (Resource Recommender Module)
        # Assuming 500 officers on shift; optimizing based on crowd demand and the compound multiplier
        opt_result = await optimize_manpower(
            total_officers=500,
            demands={"Primary_Event": max(10, int(request.expected_crowd / 150))},
            risks={"Primary_Event": compound_multiplier}
        )
        
        assigned_cops = opt_result["allocations"].get("Primary_Event", 5)
        
        resources_payload = {
            "police": assigned_cops,
            "traffic": max(2, int(assigned_cops * 0.4)), # 40% are traffic wardens
            "ambulance": 3 if compound_multiplier >= 1.5 else 1,
            "fire": 2 if "fire" in request.event_cause.lower() else 0,
            "status": opt_result.get("optimization_status", "Optimal")
        }

        # 4. Tactical Routing Engine
        origin_lat = getattr(request, 'latitude', 12.9716) - 0.005
        origin_lon = getattr(request, 'longitude', 77.5946) - 0.005
        dest_lat = getattr(request, 'latitude', 12.9716) + 0.005
        dest_lon = getattr(request, 'longitude', 77.5946) + 0.005
        
        diversion_routes = None
        formatted_barricades = []
        
        try:
            routing_res = await calculate_tactical_diversion(
                corridor=request.corridor, o_lat=origin_lat, o_lon=origin_lon, d_lat=dest_lat, d_lon=dest_lon
            )
            if routing_res and routing_res.get("status") == "Optimal Diversion Found":
                diversion_routes = routing_res.get("route_geojson")
                for p in routing_res.get("barricade_points", []):
                    if isinstance(p, dict) and p.get("lon") and p.get("lat"):
                        formatted_barricades.append([float(p["lon"]), float(p["lat"])])
                    elif isinstance(p, (list, tuple)) and len(p) >= 2:
                        formatted_barricades.append([float(p[1]), float(p[0])])
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            
        if not formatted_barricades:
            construction_coords = await _get_construction_coordinates(request.corridor)
            formatted_barricades = [[float(c[1]), float(c[0])] for c in construction_coords if len(c) >= 2]

        # 5. Pack ALL Intelligence into the Task Store
        _TASK_STORE[task_id] = {
            "status": "completed",
            "operational_order": order_text,
            "barricades": formatted_barricades,
            "diversion_routes": diversion_routes,
            "resources": resources_payload,
            "compound_threats": {
                "has_construction": has_construction,
                "multiplier": compound_multiplier
            }
        }
    except Exception as e:
        logger.error(f"Copilot background task failed: {e}")
        _TASK_STORE[task_id] = {"status": "failed", "error": str(e)}

@router.post("/generate", response_model=TaskResponse)
async def generate(request: CopilotRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    _TASK_STORE[task_id] = {"status": "processing"}
    background_tasks.add_task(background_generate_order, task_id, request)
    return TaskResponse(task_id=task_id, status="processing", message="Threat analysis started.")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    task = _TASK_STORE.get(task_id)
    if not task:
        return {"status": "failed", "error": "Task not found"}
        
    if task["status"] == "completed":
        return {
            "status": "completed", 
            "operational_order": task["operational_order"],
            "barricades": task.get("barricades", []),
            "diversion_routes": task.get("diversion_routes", None),
            "resources": task.get("resources", None),
            "compound_threats": task.get("compound_threats", None) # EXPOSING THE DATA TO REACT
        }
    return task