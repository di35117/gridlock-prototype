import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('modules.osint_harvester.service.get_gemini_client')
@patch('modules.osint_harvester.service.predict')
@patch('modules.osint_harvester.service.register_active_event')
@patch('modules.osint_harvester.service.notifier.broadcast_alert')
async def test_osint_webhook_pipeline(mock_broadcast, mock_register, mock_predict, mock_gemini, async_client):
    # Fake the LightGBM response
    mock_predict.return_value = {"compound_risk_score": 0.85, "closure_probability": 0.85, "risk_level": "High"}
    mock_register.return_value = {"message": "Queued"}
    
    # Fake the new Gemini SDK Response
    mock_response = AsyncMock()
    mock_response.text = '{"corridor": "MG Road", "event_cause": "protest", "expected_crowd": 500, "hours_from_now": 2, "duration_hours": 4}'
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    payload = {"raw_text": "Protest at MG Road today.", "source": "Twitter"}
    response = await async_client.post("/api/osint/webhook", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "Accepted"