from fastapi import APIRouter
from modules.learning_engine import service
from modules.learning_engine.models import PostEventFeedbackRequest, PostEventFeedbackResponse

router = APIRouter(prefix="/api/learning", tags=["Learning Engine"])

@router.post("/feedback", response_model=PostEventFeedbackResponse)
async def log_feedback(request: PostEventFeedbackRequest):
    result = await service.process_learning_feedback(
        corridor=request.corridor,
        event_cause=request.event_cause,
        predicted_risk=request.predicted_risk_score,
        observed_ratio=request.observed_congestion_ratio
    )
    return PostEventFeedbackResponse(**result)