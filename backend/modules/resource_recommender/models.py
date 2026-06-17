from pydantic import BaseModel, Field
from typing import Dict, List

class TacticalRequest(BaseModel):
    corridor: str = Field(..., description="The event corridor")
    risk_level: str = Field(..., description="Risk level from the forecaster (Low, Medium, High, Critical)")

class TacticalResponse(BaseModel):
    primary_stations: List[str]
    manpower_tier: str
    recommended_barricade_count: int

class OptimizeRequest(BaseModel):
    total_available_officers: int = Field(..., description="Total manpower available this shift")
    event_demands: Dict[str, int] = Field(..., description="Dictionary of Event Name -> Required Officers")
    event_risks: Dict[str, float] = Field(..., description="Dictionary of Event Name -> Compound Risk Score")

class OptimizeResponse(BaseModel):
    allocations: Dict[str, int]
    unmet_demand: int
    optimization_status: str