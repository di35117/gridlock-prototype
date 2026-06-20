import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# ─────────────────────────────────────────────────────────
# 1. Standard Surge Detection (Found in DB)
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.surge_detector.service.engine')
async def test_surge_detection_math(mock_engine, async_client):
    """Tests the standard Z-score math when baselines are found in the DB."""
    
    # Cleanly mock the DB row response
    mock_row = MagicMock()
    mock_row.avg_hourly_baseline = 10.0
    mock_row.std_hourly_baseline = 2.0
    
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Test Normal Traffic: 12 incidents. Math: (12 - 10) / 2 = 1.0 Z-Score
    res_normal = await async_client.post("/api/surge/check", json={"corridor": "Hosur Road", "current_hourly_incidents": 12})
    assert res_normal.status_code == 200
    data_normal = res_normal.json()
    assert data_normal["z_score"] == 1.0
    assert data_normal["is_surge_detected"] is False

    # Test Surge Traffic: 15 incidents. Math: (15 - 10) / 2 = 2.5 Z-Score
    res_surge = await async_client.post("/api/surge/check", json={"corridor": "Hosur Road", "current_hourly_incidents": 15})
    assert res_surge.status_code == 200
    data_surge = res_surge.json()
    assert data_surge["z_score"] == 2.5
    assert data_surge["is_surge_detected"] is True


# ─────────────────────────────────────────────────────────
# 2. Fallback Default Baseline Logic
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.surge_detector.service.engine')
async def test_surge_fallback_default_baseline(mock_engine, async_client):
    """Verifies safe fallback to 5.0 mean and 2.0 std if the corridor is completely unknown."""
    
    # Mock the DB returning None (No historical row found)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Test with 10 incidents. Expected Fallback Math: (10 - 5.0) / 2.0 = 2.5 Z-score
    res = await async_client.post("/api/surge/check", json={"corridor": "Unknown Dirt Road", "current_hourly_incidents": 10})
    
    assert res.status_code == 200
    data = res.json()
    
    assert data["baseline_mean"] == 5.0
    assert data["baseline_std"] == 2.0
    assert data["z_score"] == 2.5
    assert data["is_surge_detected"] is True


# ─────────────────────────────────────────────────────────
# 3. Zero Standard Deviation Safeguard
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.surge_detector.service.engine')
async def test_surge_zero_std_safeguard(mock_engine, async_client):
    """Verifies that a standard deviation of 0.0 defaults to 1.0 to prevent division by zero errors."""
    
    # Mock DB returning 0.0 for standard deviation
    mock_row = MagicMock()
    mock_row.avg_hourly_baseline = 8.0
    mock_row.std_hourly_baseline = 0.0
    
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # If std was 0, it would crash. Safe fallback makes std=1.0. 
    # Math check: (11 - 8.0) / 1.0 = 3.0 Z-score
    res = await async_client.post("/api/surge/check", json={"corridor": "Quiet Road", "current_hourly_incidents": 11})
    
    assert res.status_code == 200
    data = res.json()
    
    assert data["baseline_std"] == 1.0  # Safeguard applied successfully
    assert data["z_score"] == 3.0
    assert data["is_surge_detected"] is True