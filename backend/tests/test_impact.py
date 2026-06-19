import pytest
from unittest.mock import patch

@pytest.mark.asyncio
@patch('modules.impact_forecaster.service.predict') 
async def test_forecast_predict_endpoint(mock_predict, async_client):
    # FIX: Provide the full dictionary of fields that the Pydantic model expects
    mock_predict.return_value = {
        "event_cause": "vehicle_breakdown",
        "corridor": "ORR East",
        "hour_of_day": 14,
        "day_of_week": 2,
        "corridor_risk_score": 75.0,
        "closure_probability": 0.88,
        "priority_prediction": "Critical",
        "risk_level": "Severe",
        "priority_probability": 0.9,
        "closure_prediction": True,
        "corridor_closure_rate": 0.5,
        "corridor_high_priority_rate": 0.5,
        "cause_closure_rate": 0.5,
        "cause_severity_tier": "High",
        "compound_risk_score": 0.85,
        "known_corridor": True,
        "known_cause": True
    }

    payload = {
        "event_cause": "vehicle_breakdown", "corridor": "ORR East",
        "hour_of_day": 14, "day_of_week": 2, "latitude": 12.9,
        "longitude": 77.5, "veh_type": "heavy_vehicle"
    }

    response = await async_client.post("/api/forecast/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["closure_probability"] == 0.88