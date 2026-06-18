from fastapi import APIRouter
from modules.osint_harvester import service
from modules.osint_harvester.models import OSINTRequest, OSINTResponse

router = APIRouter(prefix="/api/osint", tags=["OSINT Harvester"])

@router.post("/process", response_model=OSINTResponse)
async def process_intel(request: OSINTRequest):
    result = await service.process_osint_intel(
        raw_text=request.raw_text,
        source=request.source
    )
    return OSINTResponse(**result)