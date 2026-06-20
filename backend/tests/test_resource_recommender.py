import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# ─────────────────────────────────────────────────────────
# 1. Tactical Plan Endpoint - Historical Mapping Found
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.resource_recommender.service.engine')
async def test_tactical_plan_success(mock_engine, async_client):
    """Verifies tactical plan matches historical stations and correctly sets risk tiers."""
    
    # Mocking SQLAlchemy engine async connection and execution pipeline
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    
    # Simulate database rows returned from station_corridor_mapping
    mock_row_1 = MagicMock()
    mock_row_1.police_station = "Ulsoor Police Station"
    mock_row_2 = MagicMock()
    mock_row_2.police_station = "Cubbon Park Police Station"
    
    mock_result.fetchall.return_value = [mock_row_1, mock_row_2]
    mock_conn.execute.return_value = mock_result
    
    # Configure mock engine context manager
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    payload = {
        "corridor": "MG Road",
        "risk_level": "High"
    }
    
    response = await async_client.post("/api/recommend/tactical", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert historical stations are mapped and parsed correctly
    assert "Ulsoor Police Station" in data["primary_stations"]
    assert "Cubbon Park Police Station" in data["primary_stations"]
    
    # Assert tier mapping logic for "High" risk levels
    assert data["manpower_tier"] == "Tier 1 (Major Deployment)"
    assert data["recommended_barricade_count"] == 40


# ─────────────────────────────────────────────────────────
# 2. Tactical Plan Endpoint - Fallback Logic
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.resource_recommender.service.engine')
async def test_tactical_plan_fallback(mock_engine, async_client):
    """Verifies system safely falls back when no historical station mapping exists."""
    
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [] # No rows found
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    payload = {
        "corridor": "Unknown Dark Alley Road",
        "risk_level": "Critical"
    }
    
    response = await async_client.post("/api/recommend/tactical", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert default fallback message triggers cleanly
    assert data["primary_stations"] == ["Nearest available station (No historical mapping)"]
    assert data["manpower_tier"] == "Tier 0 (Maximum Mobilization)"
    assert data["recommended_barricade_count"] == 100


# ─────────────────────────────────────────────────────────
# 3. PuLP Linear Programming Optimization Test
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manpower_optimization_pulp(async_client):
    """Validates the mathematical correctness of the PuLP optimization engine."""
    
    # Setup Scenario:
    # Available Officers = 50
    # Event A (High Risk: 0.90) demands 30 officers.
    # Event B (Med Risk:  0.50) demands 40 officers.
    # Mathematical expectation: Event A gets filled entirely (30), Event B gets the remaining (20).
    # Unmet demand: (30 + 40) - 50 = 20.
    payload = {
        "total_available_officers": 50,
        "event_demands": {
            "Protest_A": 30,
            "VIP_Convoy_B": 40
        },
        "event_risks": {
            "Protest_A": 0.90,
            "VIP_Convoy_B": 0.50
        }
    }
    
    response = await async_client.post("/api/recommend/optimize", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify optimization state and target allocations
    assert data["optimization_status"] == "Optimal"
    assert data["allocations"]["Protest_A"] == 30
    assert data["allocations"]["VIP_Convoy_B"] == 20
    assert data["unmet_demand"] == 20