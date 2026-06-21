from fastapi import APIRouter, BackgroundTasks
from modules.ai_copilot import service
from modules.ai_copilot.models import CopilotRequest, TaskResponse
import uuid
import logging
from modules.routing_engine.service import calculate_tactical_diversion, _get_construction_coordinates

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])
logger = logging.getLogger(__name__)

# Temporary in-memory dictionary to store finished background tactical tasks
_TASK_STORE = {}

async def background_generate_order(task_id: str, request: CopilotRequest):
    """The background worker function that links Gemini and the Routing Engine."""
    try:
        # 1. Generate the LLM Text Operational Report via Gemini
        order_text = await service.generate_operational_order(
            event_cause=request.event_cause,
            corridor=request.corridor,
            expected_crowd=request.expected_crowd,
            event_details=request.event_details,
            event_datetime=request.event_datetime
        )
        
        # 2. Derive approach & bypass points around the threat hotspot center
        origin_lat = request.latitude - 0.005
        origin_lon = request.longitude - 0.005
        dest_lat = request.latitude + 0.005
        dest_lon = request.longitude + 0.005
        
        diversion_routes = None
        formatted_barricades = []
        
        try:
            # Execute heavy OpenStreetMap route graph calculations 
            routing_res = await calculate_tactical_diversion(
                corridor=request.corridor,
                o_lat=origin_lat,
                o_lon=origin_lon,
                d_lat=dest_lat,
                d_lon=dest_lon
            )
            
            if routing_res and routing_res.get("status") == "Optimal Diversion Found":
                diversion_routes = routing_res.get("route_geojson")
                barricade_points = routing_res.get("barricade_points", [])
                
                # CRITICAL: Transform barricade formats safely into MapLibre [[lon, lat]] coordinates
                for p in barricade_points:
                    if isinstance(p, dict):
                        lon = p.get("lon") or p.get("longitude")
                        lat = p.get("lat") or p.get("latitude")
                        if lon is not None and lat is not None:
                            formatted_barricades.append([float(lon), float(lat)])
                    elif isinstance(p, (list, tuple)) and len(p) >= 2:
                        formatted_barricades.append([float(p[1]), float(p[0])])
                        
        except Exception as routing_err:
            logger.error(f"Tactical routing execution engine failed: {routing_err}")
            
        # Fallback: If no dedicated path barrier is isolated, block local active construction nodes
        if not formatted_barricades:
            try:
                construction_coords = await _get_construction_coordinates(request.corridor)
                formatted_barricades = [[float(c[1]), float(c[0])] for c in construction_coords if len(c) >= 2]
            except Exception as fallback_err:
                logger.error(f"Fallback construction coordinate capture failed: {fallback_err}")
                
        # 3. Formulate standard payload requirements to satisfy the UI Resource Dashboard
        resources_payload = {
            "police": max(2, int(request.expected_crowd / 200)),
            "traffic": max(2, int(request.expected_crowd / 400)),
            "ambulance": 3 if request.expected_crowd > 2500 else 1,
            "fire": 2 if "fire" in request.event_cause.lower() or "structural" in request.event_details.lower() else 0,
            "status": "Optimal"
        }

        # Cache completed calculation parameters
        _TASK_STORE[task_id] = {
            "status": "completed",
            "operational_order": order_text,
            "barricades": formatted_barricades,
            "diversion_routes": diversion_routes,
            "resources": resources_payload
        }
    except Exception as e:
        logger.error(f"Copilot background task processing failed: {e}")
        _TASK_STORE[task_id] = {"status": "failed", "error": str(e)}

@router.post("/generate", response_model=TaskResponse)
async def generate(request: CopilotRequest, background_tasks: BackgroundTasks):
    """Instantly accepts the request and pushes routing and LLM logic to background."""
    task_id = str(uuid.uuid4())
    _TASK_STORE[task_id] = {"status": "processing"}
    
    background_tasks.add_task(background_generate_order, task_id, request)
    
    return TaskResponse(
        task_id=task_id, 
        status="processing", 
        message="Threat analysis and multi-layer route calculations initialized."
    )

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Endpoint for frontend dashboard client to poll for completed tasks."""
    task = _TASK_STORE.get(task_id)
    if not task:
        return {"status": "failed", "error": "Task not found"}
        
    if task["status"] == "completed":
        return {
            "status": "completed", 
            "operational_order": task["operational_order"],
            "barricades": task.get("barricades", []),
            "diversion_routes": task.get("diversion_routes", None),
            "resources": task.get("resources", None)
        }
        
    return task