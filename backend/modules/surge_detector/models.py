from pydantic import BaseModel, Field

class SurgeRequest(BaseModel):
    corridor: str = Field(..., description="The corridor being monitored")
    current_hourly_incidents: int = Field(..., description="Number of incidents reported in the last 60 minutes")

class SurgeResponse(BaseModel):
    corridor: str
    baseline_mean: float
    baseline_std: float
    current_incidents: int
    z_score: float
    is_surge_detected: bool
    automated_action: str | None