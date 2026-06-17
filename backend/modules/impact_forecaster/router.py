"""
API routes for the Impact Forecaster module (Pain Point 1).
"""

import logging
from fastapi import APIRouter, HTTPException

from modules.impact_forecaster import trainer, service
from modules.impact_forecaster.models import ForecastRequest, ForecastResponse, TrainResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forecast", tags=["Impact Forecaster"])


@router.get("/status")
async def status():
    return {"models_trained": trainer.models_exist()}


@router.post("/train", response_model=TrainResponse)
async def train():
    """Train (or retrain) the priority + road-closure classifiers on all incidents in the DB."""
    try:
        metrics = await trainer.train_and_save()
    except Exception as exc:
        logger.exception("Training failed")
        raise HTTPException(status_code=500, detail=str(exc))

    service.reload_models()

    return TrainResponse(
        status="trained",
        training_samples=metrics["training_samples"],
        priority=metrics["priority"],
        closure=metrics["closure"],
    )


@router.post("/predict", response_model=ForecastResponse)
async def predict(request: ForecastRequest):
    """Forecast event impact. Pass start_datetime, OR both hour_of_day and day_of_week."""
    if request.start_datetime is None and (request.hour_of_day is None or request.day_of_week is None):
        raise HTTPException(
            status_code=422,
            detail="Provide start_datetime, or both hour_of_day and day_of_week.",
        )

    try:
        result = await service.predict(
            event_cause=request.event_cause,
            corridor=request.corridor,
            hour_of_day=request.hour_of_day,
            day_of_week=request.day_of_week,
            start_datetime=request.start_datetime,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return ForecastResponse(**result)