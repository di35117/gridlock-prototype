"""
Schemas for the Compound Conflict Detector.
"""
from pydantic import BaseModel, Field
from typing import List

class ConflictRequest(BaseModel):
    corridor: str = Field(..., description="The corridor where the event is planned")
    event_cause: str = Field(..., description="The planned event type")

class ConflictResponse(BaseModel):
    corridor: str
    event_cause: str
    base_risk_score: float
    construction_incident_count: int
    cause_closure_rate: float
    compound_multiplier: float
    compound_risk_score: float
    risk_level: str
    warnings: List[str]