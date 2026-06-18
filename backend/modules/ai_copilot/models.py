"""
Schemas for the AI Copilot module.
"""
from pydantic import BaseModel, Field
from datetime import datetime

class CopilotRequest(BaseModel):
    event_cause: str = Field(..., description="Type of event, e.g., public_event")
    corridor: str = Field(..., description="Location of the event")
    expected_crowd: int = Field(1000, description="Estimated attendance")
    event_details: str = Field("", description="Additional context from the officer")
    event_datetime: datetime = Field(..., description="When the event occurs")

class CopilotResponse(BaseModel):
    operational_order: str = Field(..., description="Markdown formatted operational plan")