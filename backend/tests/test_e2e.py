import pytest
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
@patch("modules.osint_harvester.service.get_gemini_client")
@patch("modules.osint_harvester.service.predict")
@patch("modules.osint_harvester.service.register_active_event")
@patch("modules.resource_recommender.service.engine")
@patch("modules.routing_engine.service.calculate_tactical_diversion")
@patch("modules.websockets.manager.ConnectionManager.broadcast_alert")
async def test_full_platform_end_to_end(
    mock_broadcast,
    mock_routing,
    mock_db_engine,
    mock_register,
    mock_predict,
    mock_gemini,
    async_client
):
    """
    Master Integration Test: Simulates the complete lifecycle of a traffic incident 
    from social media detection to UI broadcast, resource allocation, and map routing.
    """
    
    # ─────────────────────────────────────────────────────────
    # SETUP: MOCK EXTERNAL DEPENDENCIES (LLM, ML, Graph, DB)
    # ─────────────────────────────────────────────────────────
    
    # Fake Gemini extracting JSON from the raw tweet
    mock_response = AsyncMock()
    mock_response.text = '{"corridor": "MG Road", "event_cause": "protest", "expected_crowd": 1000, "hours_from_now": 0, "duration_hours": 3}'
    mock_gemini_instance = AsyncMock()
    mock_gemini_instance.aio.models.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_gemini_instance

    # Fake LightGBM Forecaster returning a severe risk probability
    mock_predict.return_value = {
        "compound_risk_score": 0.95, 
        "closure_probability": 0.92, 
        "risk_level": "Critical"
    }
    
    # Fake Learning Engine DB Registration
    mock_register.return_value = {"message": "Successfully registered in Memory Engine"}

    # Fake Resource Recommender DB Fallback 
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [] # No exact historical match found
    mock_conn.execute.return_value = mock_result
    mock_db_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Fake Routing Engine Map Graph Output
    mock_routing.return_value = {
        "status": "Optimal Diversion Found",
        "route_geojson": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[77.5, 12.9], [77.6, 12.9]]}},
        "barricade_points": [{"latitude": 12.9, "longitude": 77.5}],
        "blocked_construction_nodes": 1
    }

    # ─────────────────────────────────────────────────────────
    # PHASE 1: OSINT INTELLIGENCE INGESTION
    # ─────────────────────────────────────────────────────────
    
    payload = {"raw_text": "Massive protest blocking MG Road right now!", "source": "Twitter"}
    osint_res = await async_client.post("/api/osint/process", json=payload)
    
    assert osint_res.status_code == 200
    osint_data = osint_res.json()
    assert osint_data["status"] == "OSINT Processing Complete"
    
    extracted_corridor = osint_data["extracted_data"]["corridor"]
    
    # Verify the background WebSocket broadcast was successfully triggered to alert the UI
    mock_broadcast.assert_called_once()
    broadcast_arg = mock_broadcast.call_args[0][0]
    assert broadcast_arg["corridor"] == "MG Road"
    assert broadcast_arg["risk_level"] == "Critical"
    assert broadcast_arg["type"] == "CRITICAL_ALERT"

    # ─────────────────────────────────────────────────────────
    # PHASE 2: TACTICAL RESOURCE ALLOCATION (Triggered by UI)
    # ─────────────────────────────────────────────────────────
    
    tactical_res = await async_client.post("/api/recommend/tactical", json={
        "corridor": extracted_corridor,
        "risk_level": "Critical"
    })
    
    assert tactical_res.status_code == 200
    tactical_data = tactical_res.json()
    
    # Because risk is Critical, it must upgrade to Tier 0 deployment automatically
    assert tactical_data["manpower_tier"] == "Tier 0 (Maximum Mobilization)"
    assert tactical_data["recommended_barricade_count"] == 100

    # ─────────────────────────────────────────────────────────
    # PHASE 3: ROUTING & MAP DIVERSION (Triggered by UI)
    # ─────────────────────────────────────────────────────────
    
    routing_res = await async_client.post("/api/routing/diversion", json={
        "corridor": extracted_corridor,
        "origin_lat": 12.90,
        "origin_lon": 77.50,
        "dest_lat": 12.92,
        "dest_lon": 77.52
    })
    
    assert routing_res.status_code == 200
    routing_data = routing_res.json()
    
    assert routing_data["status"] == "Optimal Diversion Found"
    assert len(routing_data["barricade_points"]) > 0
    assert routing_data["route_geojson"]["geometry"]["type"] == "LineString"