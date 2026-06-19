import pytest
from unittest.mock import patch

@pytest.mark.asyncio
@patch('modules.impact_forecaster.service.predict') # FIX: Patched the correct public function
async def test_forecast_predict_endpoint(mock_predict, async_client):
    mock_predict.return_value = {
        "corridor_risk_score": 75.0,
        "closure_probability": 0.88,
        "priority_prediction": "Critical",
        "risk_level": "Severe"
    }

    payload = {
        "event_cause": "vehicle_breakdown", "corridor": "ORR East",
        "hour_of_day": 14, "day_of_week": 2, "latitude": 12.9,
        "longitude": 77.5, "veh_type": "heavy_vehicle"
    }

    response = await async_client.post("/api/forecast/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["closure_probability"] == 0.88