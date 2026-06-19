import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('modules.surge_detector.service.engine.connect')
async def test_surge_detection_math(mock_db_connect, async_client):
    class MockRow:
        def fetchone(self):
            class Result:
                avg_hourly_baseline = 10.0
                std_hourly_baseline = 2.0
            return Result()
            
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = MockRow()
    mock_db_connect.return_value.__aenter__.return_value = mock_conn

    # Normal traffic
    res_normal = await async_client.post("/api/surge/check", json={"corridor": "Hosur Road", "current_hourly_incidents": 12})
    assert res_normal.json()["z_score"] == 1.0
    assert res_normal.json()["is_surge_detected"] is False

    # Surge anomaly
    res_surge = await async_client.post("/api/surge/check", json={"corridor": "Hosur Road", "current_hourly_incidents": 15})
    assert res_surge.json()["z_score"] == 2.5
    assert res_surge.json()["is_surge_detected"] is True