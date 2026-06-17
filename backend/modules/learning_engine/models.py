from pydantic import BaseModel, Field
from typing import Optional

class PostEventFeedbackRequest(BaseModel):
    corridor: str = Field(..., description="The corridor where the event occurred")
    event_cause: str = Field(..., description="The type of event")
    predicted_risk_score: float = Field(..., description="What the system originally predicted")
    observed_congestion_ratio: Optional[float] = Field(None, description="Simulated observed travel time ratio (e.g., 2.1x normal)")

class PostEventFeedbackResponse(BaseModel):
    corridor: str
    event_cause: str
    predicted_severity: float
    observed_severity: float
    previous_calibration: float
    new_calibration_factor: float
    learning_insight: str