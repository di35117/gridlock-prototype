"""
Schemas for the Autonomous Learning Engine.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EventRegistrationRequest(BaseModel):
    event_id: str = Field(..., description="Unique tracking ID for the specific event")
    corridor: str = Field(..., description="The corridor where the event is occurring")
    event_cause: str = Field(..., description="The type of event")
    predicted_risk_score: float = Field(..., description="The original risk forecast")
    expected_end_time: datetime = Field(..., description="When the event is scheduled to finish")

class EventRegistrationResponse(BaseModel):
    status: str
    message: str

class PostEventFeedbackRequest(BaseModel):
    corridor: str = Field(..., description="The corridor where the event occurred")
    event_cause: str = Field(..., description="The type of event")
    predicted_risk_score: float = Field(..., description="What the system originally predicted")
    observed_congestion_ratio: Optional[float] = Field(None, description="Provide to override automated polling")
    is_demo_mode: bool = Field(True, description="If true, simulates a real-world API spike")

class PostEventFeedbackResponse(BaseModel):
    corridor: str
    event_cause: str
    predicted_severity: float
    observed_severity: float
    previous_calibration: float
    new_calibration_factor: float
    learning_insight: str