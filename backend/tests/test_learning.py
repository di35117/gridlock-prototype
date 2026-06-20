import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from modules.learning_engine.service import autonomous_event_learning_scan

# ─────────────────────────────────────────────────────────
# 1. Event Registration Endpoint
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.learning_engine.service.redis_client')
async def test_register_event_success(mock_redis, async_client):
    """Verifies that an incoming event is properly formatted and stored in Redis."""
    # Setup mock to do nothing successfully
    mock_redis.set.return_value = True
    
    end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    payload = {
        "event_id": "EVT-TEST-101",
        "corridor": "Hebbal Flyover",
        "event_cause": "accident",
        "predicted_risk_score": 0.88,
        "expected_end_time": end_time
    }
    
    response = await async_client.post("/api/learning/register", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Ensure it was written to Redis with the correct prefix
    mock_redis.set.assert_called_once()
    args, _ = mock_redis.set.call_args
    assert args[0] == "active_event:EVT-TEST-101"
    assert "Hebbal Flyover" in args[1]


# ─────────────────────────────────────────────────────────
# 2. Feedback Loop & EMA Math Verification
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.learning_engine.service.redis_client')
async def test_feedback_endpoint_ema_calculation(mock_redis, async_client):
    """
    Tests the Exponential Moving Average (EMA) math.
    If the system predicted 0.5 risk, but observed 1.0 (double the risk),
    the calibration factor should increase to punish the under-prediction.
    """
    # Mock previous calibration factor sitting in Redis at 1.0
    mock_redis.get.return_value = "1.0"
    mock_redis.set.return_value = True
    
    payload = {
        "corridor": "Silk Board",
        "event_cause": "construction",
        "predicted_risk_score": 0.5,
        "observed_congestion_ratio": 1.0,  # 1.0 / 0.5 = 2.0 error ratio
        "is_demo_mode": False
    }
    
    response = await async_client.post("/api/learning/feedback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["previous_calibration"] == 1.0
    
    # EMA Math Check: Alpha = 0.3
    # New Calib = (0.3 * 2.0) + (0.7 * 1.0) = 0.6 + 0.7 = 1.3
    assert data["new_calibration_factor"] == 1.3
    
    # Ensure the new factor was saved to Redis
    mock_redis.set.assert_called_with("calibration:construction", 1.3)


# ─────────────────────────────────────────────────────────
# 3. Autonomous Daemon Operations
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.learning_engine.service.process_learning_feedback')
@patch('modules.learning_engine.service.redis_client')
async def test_daemon_processes_expired_event(mock_redis, mock_feedback):
    """Verifies the daemon finds events whose time has expired, triggers learning, and deletes them."""
    
    # Create a timestamp from 1 hour AGO (meaning the event has finished)
    past_time = (datetime.now() - timedelta(hours=1)).isoformat()
    
    # Mock Redis finding 1 active event
    mock_redis.keys.return_value = ["active_event:EVT-EXPIRED"]
    mock_redis.get.return_value = json.dumps({
        "corridor": "ORR East",
        "event_cause": "protest",
        "predicted_risk": 0.75,
        "expected_end_time": past_time
    })
    
    # Run the daemon manually
    await autonomous_event_learning_scan()
    
    # 1. Verify it triggered the feedback loop for that specific event
    mock_feedback.assert_called_once_with(
        corridor="ORR East",
        event_cause="protest",
        predicted_risk=0.75,
        observed_ratio=None,
        is_demo_mode=True
    )
    
    # 2. Verify it deleted the event from Redis so it doesn't process it again
    mock_redis.delete.assert_called_once_with("active_event:EVT-EXPIRED")


@pytest.mark.asyncio
@patch('modules.learning_engine.service.process_learning_feedback')
@patch('modules.learning_engine.service.redis_client')
async def test_daemon_ignores_ongoing_event(mock_redis, mock_feedback):
    """Verifies the daemon safely ignores active events whose end times are in the future."""
    
    # Create a timestamp 1 hour in the FUTURE
    future_time = (datetime.now() + timedelta(hours=1)).isoformat()
    
    mock_redis.keys.return_value = ["active_event:EVT-ONGOING"]
    mock_redis.get.return_value = json.dumps({
        "corridor": "Mysore Road",
        "event_cause": "vip_movement",
        "predicted_risk": 0.4,
        "expected_end_time": future_time
    })
    
    # Run the daemon
    await autonomous_event_learning_scan()
    
    # Verify the feedback loop was NOT called and the event was NOT deleted
    mock_feedback.assert_not_called()
    mock_redis.delete.assert_not_called()