import pytest
from unittest.mock import patch

@pytest.mark.asyncio
@patch('modules.cctv_ingestion.service.predict')
@patch('modules.cctv_ingestion.service.register_active_event')
async def test_cctv_webhook_perfect_payload(mock_register, mock_predict, async_client):
    mock_predict.return_value = {"compound_risk_score": 0.9, "risk_level": "High", "closure_probability": 0.8}
    mock_register.return_value = None
    
    payload = {
        "corridor": "Mysore Road",
        "event_cause": "vehicle_breakdown",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "veh_type": "heavy_vehicle"
    }
    response = await async_client.post("/api/cctv/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "Accepted"

@pytest.mark.asyncio
async def test_cctv_webhook_rejects_arrays(async_client):
    bad_payload = [{"cam_id": 1, "status": "broken"}]
    response = await async_client.post("/api/cctv/webhook", json=bad_payload)
    assert response.status_code == 200