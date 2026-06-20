import pytest
from unittest.mock import patch, AsyncMock

# ─────────────────────────────────────────────────────────
# 1. Background Webhook Endpoint Test
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.osint_harvester.service.get_gemini_client')
@patch('modules.osint_harvester.service.predict')
@patch('modules.osint_harvester.service.register_active_event')
@patch('modules.osint_harvester.service.notifier.broadcast_alert')
async def test_osint_webhook_pipeline(mock_broadcast, mock_register, mock_predict, mock_gemini, async_client):
    """Verifies that the webhook accepts the payload and safely triggers the background task."""
    
    # Fake the LightGBM response
    mock_predict.return_value = {"compound_risk_score": 0.85, "closure_probability": 0.85, "risk_level": "High"}
    mock_register.return_value = {"message": "Queued"}
    
    # Fake the Gemini SDK Response
    mock_response = AsyncMock()
    mock_response.text = '{"corridor": "MG Road", "event_cause": "protest", "expected_crowd": 500, "hours_from_now": 2, "duration_hours": 4}'
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    payload = {"raw_text": "Protest at MG Road today.", "source": "Twitter"}
    response = await async_client.post("/api/osint/webhook", json=payload)
    
    # We expect a 200 Accepted because processing moves immediately to a background task
    assert response.status_code == 200
    assert response.json()["status"] == "Accepted"


# ─────────────────────────────────────────────────────────
# 2. Manual Process Endpoint Test (Full Pipeline Validation)
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.osint_harvester.service.get_gemini_client')
@patch('modules.osint_harvester.service.predict')
@patch('modules.osint_harvester.service.register_active_event')
@patch('modules.osint_harvester.service.notifier.broadcast_alert')
async def test_osint_manual_process_success(mock_broadcast, mock_register, mock_predict, mock_gemini, async_client):
    """Verifies the complete synchronous pipeline: LLM Extraction -> ML Prediction -> Registration -> Broadcast."""
    
    # Fake the LightGBM forecast
    mock_predict.return_value = {
        "compound_risk_score": 0.95, 
        "closure_probability": 0.90, 
        "risk_level": "Critical"
    }
    
    # Fake Learning Engine Registration
    mock_register.return_value = {"message": "Successfully registered in Learning Engine"}
    
    # Fake Gemini extracting structured JSON from raw text
    mock_response = AsyncMock()
    mock_response.text = '{"corridor": "ORR East", "event_cause": "protest", "expected_crowd": 1000, "hours_from_now": 1, "duration_hours": 3}'
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    payload = {"raw_text": "Huge VIP convoy passing through ORR East in 1 hour.", "source": "News"}
    response = await async_client.post("/api/osint/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # 1. Assert LLM Named Entity Recognition (NER) mapping worked
    assert data["status"] == "OSINT Processing Complete"
    assert data["extracted_data"]["corridor"] == "ORR East"
    
    # 2. Assert ML pipeline details passed forward cleanly
    assert data["forecasted_risk"] == 0.95
    assert data["registration_message"] == "Successfully registered in Learning Engine"
    
    # 3. Assert all auxiliary downstream integrations fired off
    mock_predict.assert_called_once()
    mock_register.assert_called_once()
    mock_broadcast.assert_called_once()


# ─────────────────────────────────────────────────────────
# 3. LLM Parsing Failure Test
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.osint_harvester.service.get_gemini_client')
async def test_osint_gemini_json_failure(mock_gemini, async_client):
    """Verifies the system returns a server error response when Gemini returns malformed text."""
    
    # Fake Gemini returning plain text conversation instead of structured JSON
    mock_response = AsyncMock()
    mock_response.text = 'I cannot determine a traffic event from this text.'
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    payload = {"raw_text": "Just ate a great sandwich.", "source": "Twitter"}
    response = await async_client.post("/api/osint/process", json=payload)
    
    # Expecting a 500 status code because unhandled parsing exceptions inside endpoints raise internal errors
    assert response.status_code == 500