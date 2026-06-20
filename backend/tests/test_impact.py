import pytest
from unittest.mock import patch, mock_open
import json

# ─────────────────────────────────────────────────────────
# 1. Status & Metrics Endpoints
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.impact_forecaster.router.trainer.models_exist')
async def test_status_endpoint(mock_models_exist, async_client):
    """Verifies the status endpoint accurately reports model existence."""
    mock_models_exist.return_value = True
    response = await async_client.get("/api/forecast/status")
    
    assert response.status_code == 200
    assert response.json() == {"models_trained": True}


@pytest.mark.asyncio
@patch('modules.impact_forecaster.router.trainer.METRICS_PATH')
async def test_get_metrics_success(mock_metrics_path, async_client):
    """Tests fetching training metrics when the JSON file exists."""
    mock_metrics_path.exists.return_value = True
    
    mock_json_data = json.dumps({
        "training_samples": 8173,
        "priority": {"accuracy": 0.85},
        "closure": {"accuracy": 0.92}
    })
    
    # Mock opening the file so it reads our fake JSON string instead of disk
    with patch('builtins.open', mock_open(read_data=mock_json_data)):
        response = await async_client.get("/api/forecast/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["training_samples"] == 8173
        assert data["closure"]["accuracy"] == 0.92


@pytest.mark.asyncio
@patch('modules.impact_forecaster.router.trainer.METRICS_PATH')
async def test_get_metrics_not_found(mock_metrics_path, async_client):
    """Verifies a 404 is thrown if the user asks for metrics before training."""
    mock_metrics_path.exists.return_value = False
    response = await async_client.get("/api/forecast/metrics")
    
    assert response.status_code == 404
    assert "Metrics file not found" in response.json()["detail"]


# ─────────────────────────────────────────────────────────
# 2. Training Endpoint
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.impact_forecaster.router.trainer.train_and_save')
async def test_train_endpoint(mock_train, async_client):
    """Mocks the heavy LightGBM training loop and verifies payload routing."""
    mock_train.return_value = {
        "training_samples": 8173,
        "priority": {"accuracy": 0.88, "auc": 0.91, "recall": 0.85, "applied_threshold": 0.4},
        "closure": {"accuracy": 0.90, "auc": 0.94, "recall": 0.82, "applied_threshold": 0.5},
        "feature_cols": ["corridor", "hour_of_day"]
    }
    
    response = await async_client.post("/api/forecast/train")
    
    assert response.status_code == 200
    data = response.json()
    assert data["training_samples"] == 8173
    assert data["priority"]["accuracy"] == 0.88


# ─────────────────────────────────────────────────────────
# 3. Predict Endpoint
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.impact_forecaster.router.service.predict')
async def test_forecast_predict_endpoint_success(mock_predict, async_client):
    """Tests a successfully mapped prediction request."""
    # This is the test you started, completed with valid assertions!
    mock_predict.return_value = {
        "event_cause": "vehicle_breakdown",
        "corridor": "ORR East",
        "hour_of_day": 14,
        "day_of_week": 2,
        "priority_prediction": "High",
        "priority_probability": 0.9,
        "closure_prediction": True,
        "closure_probability": 0.88,
        "corridor_risk_score": 75.0,
        "corridor_closure_rate": 0.5,
        "corridor_high_priority_rate": 0.5,
        "cause_closure_rate": 0.5,
        "cause_severity_tier": 1, 
        "compound_risk_score": 0.85,
        "risk_level": "High"
    }

    payload = {
        "event_cause": "vehicle_breakdown", 
        "corridor": "ORR East",
        "hour_of_day": 14, 
        "day_of_week": 2, 
        "latitude": 12.9,
        "longitude": 77.6
    }
    
    response = await async_client.post("/api/forecast/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["priority_prediction"] == "High"
    assert data["closure_probability"] == 0.88
    mock_predict.assert_called_once()


@pytest.mark.asyncio
async def test_forecast_predict_endpoint_missing_time(async_client):
    """Verifies validation logic blocks requests lacking both datetime and hour/day."""
    payload = {
        "event_cause": "vehicle_breakdown", 
        "corridor": "ORR East"
        # Explicitly omitting start_datetime AND hour_of_day
    }
    response = await async_client.post("/api/forecast/predict", json=payload)
    
    assert response.status_code == 422
    assert "Provide start_datetime, or both hour_of_day and day_of_week" in response.json()["detail"]