from fastapi import APIRouter, HTTPException
from modules.routing_engine import service
from modules.routing_engine.models import RoutingRequest, RoutingResponse, NetworkMetricsResponse

router = APIRouter(prefix="/api/routing", tags=["Tactical Routing Engine"])

@router.post("/diversion", response_model=RoutingResponse)
async def get_diversion(request: RoutingRequest):
    try:
        result = await service.calculate_tactical_diversion(
            corridor=request.corridor,
            o_lat=request.origin_lat,
            o_lon=request.origin_lon,
            d_lat=request.dest_lat,
            d_lon=request.dest_lon
        )
        return RoutingResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Routing failed: {str(e)}")

@router.get("/network/metrics", response_model=NetworkMetricsResponse)
async def get_network_metrics():
    """
    Returns the city road network as a GeoJSON object with real-time 
    ML risk scores embedded for MapLibre data-driven styling.
    """
    try:
        geojson_data = await service.generate_network_metrics_geojson()
        return geojson_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate network metrics: {str(e)}")