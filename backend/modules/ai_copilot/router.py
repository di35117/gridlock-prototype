"""
API routes for the AI Copilot.
"""
from fastapi import APIRouter
from modules.ai_copilot import service
from modules.ai_copilot.models import CopilotRequest, CopilotResponse

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])

@router.post("/generate", response_model=CopilotResponse)
async def generate(request: CopilotRequest):
    order_text = await service.generate_operational_order(
        event_cause=request.event_cause,
        corridor=request.corridor,
        expected_crowd=request.expected_crowd,
        event_details=request.event_details
    )
    return CopilotResponse(operational_order=order_text)