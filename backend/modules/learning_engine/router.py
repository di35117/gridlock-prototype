"""
API routes for the Learning Engine.
"""
from fastapi import APIRouter
from modules.learning_engine import service
from modules.learning_engine.models import (
    PostEventFeedbackRequest, 
    PostEventFeedbackResponse,
    EventRegistrationRequest,
    EventRegistrationResponse
)

router = APIRouter(prefix="/api/learning", tags=["Learning Engine"])

@router.post("/register", response_model=EventRegistrationResponse)
async def register_event(request: EventRegistrationRequest):
    result = await service.register_active_event(
        event_id=request.event_id,
        corridor=request.corridor,
        event_cause=request.event_cause,
        predicted_risk=request.predicted_risk_score,
        expected_end_time=request.expected_end_time
    )
    return EventRegistrationResponse(**result)

@router.post("/feedback", response_model=PostEventFeedbackResponse)
async def log_feedback(request: PostEventFeedbackRequest):
    # Manual trigger endpoint (overrides autonomous loop)
    result = await service.process_learning_feedback(
        corridor=request.corridor,
        event_cause=request.event_cause,
        predicted_risk=request.predicted_risk_score,
        observed_ratio=request.observed_congestion_ratio,
        is_demo_mode=request.is_demo_mode
    )
    return PostEventFeedbackResponse(**result)