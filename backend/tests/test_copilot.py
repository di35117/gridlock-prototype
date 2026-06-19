import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

@pytest.mark.asyncio
@patch('modules.ai_copilot.service.get_gemini_client')
@patch('modules.ai_copilot.service.predict')
@patch('modules.ai_copilot.service.detect_conflict')
@patch('modules.ai_copilot.service._get_historical_stations')
async def test_copilot_generation(mock_stations, mock_conflict, mock_predict, mock_gemini, async_client):
    mock_predict.return_value = {"corridor_risk_score": 85, "closure_probability": 0.9, "priority_prediction": "High"}
    mock_conflict.return_value = {"compound_risk_score": 90, "compound_multiplier": 1.2, "construction_incident_count": 0, "warnings": []}
    mock_stations.return_value = ["Cubbon Park Station"]

    mock_response = AsyncMock()
    mock_response.text = "1. Threat Assessment: High Risk."
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    payload = {
        "event_cause": "protest", "corridor": "MG Road",
        "expected_crowd": 500, "event_details": "Peaceful but blocking traffic.",
        "event_datetime": datetime.now().isoformat()
    }
    
    response = await async_client.post("/api/copilot/generate", json=payload)
    assert response.status_code == 200
    assert "Threat Assessment" in response.json()["operational_order"]