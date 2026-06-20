import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('modules.compound_conflict.service.engine')
async def test_detect_conflict_severe_degradation(mock_engine, async_client):
    """Tests that a high baseline combined with heavy construction triggers a Critical warning."""
    # 1. Setup mock database rows
    class MockProfileRow: risk_score = 5.0
    class MockConstRow: count = 12
    class MockCauseRow: closure_rate = 0.5; severity_tier = 1

    # 2. Mock the async execution chain
    mock_conn = AsyncMock()
    mock_res_prof = AsyncMock(); mock_res_prof.fetchone.return_value = MockProfileRow()
    mock_res_cons = AsyncMock(); mock_res_cons.fetchone.return_value = MockConstRow()
    mock_res_cause = AsyncMock(); mock_res_cause.fetchone.return_value = MockCauseRow()
    
    # Return the three query results in the exact order they are called in service.py
    mock_conn.execute.side_effect = [mock_res_prof, mock_res_cons, mock_res_cause]
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # 3. Hit the router endpoint
    payload = {"corridor": "Silk Board", "event_cause": "protest"}
    response = await async_client.post("/api/conflict/detect", json=payload)
    
    # 4. Assert the math and logic
    assert response.status_code == 200
    data = response.json()
    
    assert data["base_risk_score"] == 5.0
    assert data["construction_incident_count"] == 12
    
    # Math check: Multiplier = 1.0 + (12 * 0.05 * (1.0 + 0.5)) = 1.0 + (0.6 * 1.5) = 1.9
    assert data["compound_multiplier"] == 1.9
    # Math check: Compound Score = 5.0 * 1.9 = 9.5
    assert data["compound_risk_score"] == 9.5
    
    assert data["risk_level"] == "Critical"
    assert "SEVERE: Corridor is heavily degraded. Diversion routing is mandatory." in data["warnings"]


@pytest.mark.asyncio
@patch('modules.compound_conflict.service.engine')
async def test_detect_conflict_low_risk_no_construction(mock_engine, async_client):
    """Tests the baseline fallback when no construction is present."""
    class MockProfileRow: risk_score = 2.0
    class MockConstRow: count = 0
    class MockCauseRow: closure_rate = 0.1; severity_tier = 3

    mock_conn = AsyncMock()
    mock_res_prof = AsyncMock(); mock_res_prof.fetchone.return_value = MockProfileRow()
    mock_res_cons = AsyncMock(); mock_res_cons.fetchone.return_value = MockConstRow()
    mock_res_cause = AsyncMock(); mock_res_cause.fetchone.return_value = MockCauseRow()
    
    mock_conn.execute.side_effect = [mock_res_prof, mock_res_cons, mock_res_cause]
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    payload = {"corridor": "Hebbal Flyover", "event_cause": "vehicle_breakdown"}
    response = await async_client.post("/api/conflict/detect", json=payload)
    
    data = response.json()
    assert data["compound_multiplier"] == 1.0
    assert data["compound_risk_score"] == 2.0
    assert data["risk_level"] == "Low"
    assert len(data["warnings"]) == 0