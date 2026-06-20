import pytest
from datetime import datetime, timedelta, timezone

@pytest.mark.asyncio
async def test_learning_engine_api_endpoint(async_client, mock_redis):
    # Testing HTTP 422 avoidance by using strict Pydantic ISO formatting
    end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    
    payload = {
        "event_id": "HTTP-TEST-999",
        "corridor": "Hebbal Flyover",
        "event_cause": "accident",
        "predicted_risk_score": 0.88,
        "expected_end_time": end_time
    }
    
    response = await async_client.post("/api/learning/register", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "Active Event Registered"
    assert mock_redis.set.called or mock_redis.setex.called