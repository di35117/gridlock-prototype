"""
API routes for the Compound Conflict module.
"""
from fastapi import APIRouter
from modules.compound_conflict import service
from modules.compound_conflict.models import ConflictRequest, ConflictResponse

router = APIRouter(prefix="/api/conflict", tags=["Compound Conflict Detector"])

@router.post("/detect", response_model=ConflictResponse)
async def detect(request: ConflictRequest):
    result = await service.detect_conflict(request.corridor, request.event_cause)
    return ConflictResponse(**result)