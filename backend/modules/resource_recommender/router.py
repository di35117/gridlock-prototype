from fastapi import APIRouter
from modules.resource_recommender import service
from modules.resource_recommender.models import TacticalRequest, TacticalResponse, OptimizeRequest, OptimizeResponse

router = APIRouter(prefix="/api/recommend", tags=["Resource Recommender"])

@router.post("/tactical", response_model=TacticalResponse)
async def tactical_plan(request: TacticalRequest):
    result = await service.get_tactical_plan(request.corridor, request.risk_level)
    return TacticalResponse(**result)

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize(request: OptimizeRequest):
    result = await service.optimize_manpower(
        total_officers=request.total_available_officers,
        demands=request.event_demands,
        risks=request.event_risks
    )
    return OptimizeResponse(**result)