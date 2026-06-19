import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

@pytest.mark.asyncio
@patch('modules.learning_engine.service.redis_client')
async def test_learning_engine_queue(mock_redis, async_client):
    payload = {
        "event_id": "TEST-1234", "corridor": "Hebbal Flyover",
        "event_cause": "accident", "predicted_risk": 0.88,
        "expected_end_time": (datetime.now() + timedelta(hours=1)).isoformat()
    }
    response = await async_client.post("/api/learning/register", json=payload)
    assert response.status_code == 200
    mock_redis.setex.assert_called_once()