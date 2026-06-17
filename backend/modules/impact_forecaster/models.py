"""
Pydantic request/response schemas for the Impact Forecaster module.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ForecastRequest(BaseModel):
    event_cause: str = Field(..., description="e.g. 'public_event', 'procession', 'construction', 'VIP_movement'")
    corridor: str = Field(..., description="Corridor name, e.g. 'Mysore Road'")
    start_datetime: Optional[datetime] = Field(
        None, description="Planned event start time. If omitted, hour_of_day + day_of_week must be given."
    )
    hour_of_day: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0=Monday ... 6=Sunday")

    @field_validator("event_cause", "corridor")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ForecastResponse(BaseModel):
    event_cause: str
    corridor: str
    hour_of_day: int
    day_of_week: int

    priority_prediction: str          # "High" | "Low"
    priority_probability: float       # model's probability of High

    closure_prediction: bool
    closure_probability: float

    corridor_risk_score: float
    corridor_closure_rate: float
    corridor_high_priority_rate: float
    cause_closure_rate: float
    cause_severity_tier: int

    compound_risk_score: float        # blended score for dashboard/copilot use
    risk_level: str                   # "Low" | "Medium" | "High" | "Critical"

    known_corridor: bool              # False if corridor wasn't seen in training data
    known_cause: bool


class TrainResponse(BaseModel):
    status: str
    training_samples: int
    priority: dict
    closure: dict