import pytest
from unittest.mock import patch, AsyncMock
from modules.cctv_ingestion.service import process_cctv_payload

@pytest.mark.asyncio
@patch('modules.cctv_ingestion.service.predict')
@patch('modules.cctv_ingestion.service.register_active_event')
@patch('modules.cctv_ingestion.service.notifier.broadcast_alert')
async def test_cctv_webhook_perfect_payload(mock_broadcast, mock_register, mock_predict, async_client):
    """Verifies that the web tier successfully schedules standard payloads."""
    mock_predict.return_value = {"compound_risk_score": 0.14, "risk_level": "Low", "closure_probability": 0.05}
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
@patch('modules.cctv_ingestion.service.predict')
@patch('modules.cctv_ingestion.service.register_active_event')
@patch('modules.cctv_ingestion.service.notifier.broadcast_alert')
@patch('modules.cctv_ingestion.service.get_gemini_client')
async def test_cctv_service_ai_translation_path(mock_gemini, mock_broadcast, mock_register, mock_predict):
    """
    Directly tests the background processing logic for non-standard schemas.
    Ensures that Gemini normalizes data and downstream tracking triggers execute.
    """
    # 1. Setup downstream predictions
    mock_predict.return_value = {"compound_risk_score": 0.25, "risk_level": "Medium", "closure_probability": 0.12}
    mock_register.return_value = None
    
    # 2. Mock the modern google-genai SDK response structure
    mock_response = AsyncMock()
    mock_response.text = """
    {
        "corridor": "Outer Ring Road",
        "event_cause": "accident",
        "latitude": 12.9176,
        "longitude": 77.6244,
        "veh_type": "car"
    }
    """
    mock_client_instance = AsyncMock()
    mock_client_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_client_instance

    # 3. Simulate a legacy / non-standard camera payload
    proprietary_payload = {
        "road_name": "Outer Ring Road",
        "anomaly": "car_crash",
        "lat": 12.9176,
        "lng": 77.6244
    }

    # Invoke the service directly to bypass the fire-and-forget HTTP background wrapper
    await process_cctv_payload(proprietary_payload)

    # 4. Asserts: Verify translation logic mapped everything flawlessly
    mock_gemini.assert_called_once()
    mock_predict.assert_called_once_with(
        event_cause="accident", # Mapped by AI
        corridor="Outer Ring Road", # Mapped by AI
        hour_of_day=pytest.any(int),
        day_of_week=pytest.any(int),
        latitude=12.9176,
        longitude=77.6244,
        veh_type="car"
    )
    
    # Verify learning engine and websockets fired off
    assert mock_register.called
    assert mock_broadcast.called


@pytest.mark.asyncio
@patch('modules.cctv_ingestion.service.get_gemini_client')
async def test_cctv_service_rejects_malformed_types(mock_gemini):
    """Ensures background processing safely exits without processing arrays or strings."""
    bad_payload = [{"cam_id": 1, "status": "malfunctioning"}]
    
    # If the guard clause fails, it will look for keys and crash or call Gemini
    await process_cctv_payload(bad_payload)
    
    mock_gemini.assert_not_called()