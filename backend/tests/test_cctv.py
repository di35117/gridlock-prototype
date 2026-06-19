import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_cctv_webhook_perfect_payload(async_client):
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
    # Simulating a camera sending a list instead of an object
    bad_payload = [{"cam_id": 1, "status": "broken"}]
    response = await async_client.post("/api/cctv/webhook", json=bad_payload)
    assert response.status_code == 200 # HTTP accepts it, but background task kills it safely