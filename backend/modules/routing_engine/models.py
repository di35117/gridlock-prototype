from pydantic import BaseModel, Field
from typing import List, Dict, Any

class RoutingRequest(BaseModel):
    corridor: str = Field(..., description="The corridor where the event is occurring")
    origin_lat: float = Field(..., description="Start point latitude of the diversion")
    origin_lon: float = Field(..., description="Start point longitude of the diversion")
    dest_lat: float = Field(..., description="End point latitude (where traffic needs to go)")
    dest_lon: float = Field(..., description="End point longitude")

class RoutingResponse(BaseModel):
    status: str
    route_geojson: Dict[str, Any] = Field(..., description="GeoJSON LineString for the React map to draw")
    barricade_points: List[Dict[str, float]] = Field(..., description="List of exact lat/lon for barricade placement")
    blocked_construction_nodes: int = Field(..., description="How many construction zones were avoided")

class NetworkMetricsResponse(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]] = Field(..., description="List of road segments with embedded ML risk scores")