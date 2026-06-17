from fastapi import APIRouter, HTTPException
from modules.surge_detector import service
from modules.surge_detector.models import SurgeRequest, SurgeResponse

router = APIRouter(prefix="/api/surge", tags=["Surge Detector"])

@router.post("/check", response_model=SurgeResponse)
async def check_surge(request: SurgeRequest):
    try:
        result = await service.check_for_surge(
            corridor=request.corridor, 
            current_incidents=request.current_hourly_incidents
        )
        return SurgeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))