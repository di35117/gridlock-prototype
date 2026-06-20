import pytest
import pytest_asyncio
from sqlalchemy import text
from unittest.mock import patch, AsyncMock
from database import engine

@pytest_asyncio.fixture(autouse=True)
async def cleanup_and_seed_tables():
    """
    Cleans up all data foundation tables before each test and seeds isolated mock data.
    """
    async with engine.begin() as conn:
        # Clear previous records to guarantee deterministic sort results
        await conn.execute(text("TRUNCATE TABLE incidents, corridor_risk_profiles, station_corridor_mapping, event_cause_stats CASCADE;"))
        
        # Seed Corridor Risk Profiles (One low risk, one high risk to test sorting)
        await conn.execute(text("""
            INSERT INTO corridor_risk_profiles 
            (corridor, total_incidents, road_closures, closure_rate, high_priority_count, 
             high_priority_rate, event_incidents, construction_incidents, congestion_incidents, 
             avg_hourly_baseline, std_hourly_baseline, risk_score)
            VALUES 
            ('Low Risk Lane', 5, 0, 0.0, 1, 0.2, 1, 2, 2, 1.2, 0.4, 2.1),
            ('High Risk Highway', 50, 10, 0.2, 15, 0.3, 10, 20, 20, 8.5, 2.1, 8.9);
        """))

        # Seed Station Corridor Mappings
        await conn.execute(text("""
            INSERT INTO station_corridor_mapping 
            (corridor, police_station, incident_count, event_count, is_primary)
            VALUES 
            ('High Risk Highway', 'Station A', 30, 8, TRUE),
            ('High Risk Highway', 'Station B', 20, 2, FALSE);
        """))

        # Seed Event Cause Stats
        await conn.execute(text("""
            INSERT INTO event_cause_stats 
            (event_cause, n_incidents, closure_rate, high_priority_rate, median_time_to_close_hours, severity_tier)
            VALUES 
            ('protest', 100, 0.65, 0.80, 4.5, 3),
            ('vehicle_breakdown', 50, 0.10, 0.15, 1.2, 1);
        """))
    yield
    
    # Cleanup post test
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE incidents, corridor_risk_profiles, station_corridor_mapping, event_cause_stats CASCADE;"))


@pytest.mark.asyncio
async def test_get_status_counts(async_client):
    """Verifies that the database record overview matches seeded totals."""
    response = await async_client.get("/api/data/status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["record_counts"]["corridor_risk_profiles"] == 2
    assert data["record_counts"]["station_corridor_mapping"] == 2
    assert data["record_counts"]["event_cause_stats"] == 2
    assert data["record_counts"]["incidents"] == 0


@pytest.mark.asyncio
async def test_get_corridor_profiles_sorting(async_client):
    """Verifies all corridor records are returned, sorted by risk score descending."""
    response = await async_client.get("/api/data/corridor-profiles")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    # Ensure High Risk Highway (8.9) comes before Low Risk Lane (2.1)
    assert data[0]["corridor"] == "High Risk Highway"
    assert data[0]["risk_score"] == 8.9
    assert data[1]["corridor"] == "Low Risk Lane"


@pytest.mark.asyncio
async def test_get_single_corridor_profile_success(async_client):
    """Verifies accurate single corridor payload mapping extraction."""
    response = await async_client.get("/api/data/corridor-profiles/High%20Risk%20Highway")
    assert response.status_code == 200
    
    data = response.json()
    assert data["corridor"] == "High Risk Highway"
    assert data["construction_incidents"] == 20
    assert data["risk_score"] == 8.9


@pytest.mark.asyncio
async def test_get_single_corridor_profile_not_found(async_client):
    """Confirms 404 behavior when checking an unprofiled road name."""
    response = await async_client.get("/api/data/corridor-profiles/Unknown%20Street")
    assert response.status_code == 404
    assert "Unknown Street" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_event_stats_sorting(async_client):
    """Verifies aggregated metrics are ordered by event volume frequency descending."""
    response = await async_client.get("/api/data/event-stats")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    # 'protest' (100 incidents) must precede 'vehicle_breakdown' (50 incidents)
    assert data[0]["event_cause"] == "protest"
    assert data[0]["n_incidents"] == 100
    assert data[0]["severity_tier"] == 3
    assert data[1]["event_cause"] == "vehicle_breakdown"


@pytest.mark.asyncio
async def test_get_station_mapping_success(async_client):
    """Confirms jurisdictional mapping works and orders by highest handling station."""
    response = await async_client.get("/api/data/station-mapping/High%20Risk%20Highway")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    # Station A (30 incidents) must come before Station B (20 incidents)
    assert data[0]["police_station"] == "Station A"
    assert data[0]["is_primary"] is True
    assert data[1]["police_station"] == "Station B"
    assert data[1]["is_primary"] is False


@pytest.mark.asyncio
async def test_get_station_mapping_not_found(async_client):
    """Confirms 404 is thrown when no station mappings exist for a corridor."""
    response = await async_client.get("/api/data/station-mapping/Empty%20Boulevard")
    assert response.status_code == 404
    assert "Empty Boulevard" in response.json()["detail"]


@pytest.mark.asyncio
@patch("modules.data_foundation.router.reload_data_foundation", new_callable=AsyncMock)
async def test_reload_data_foundation_endpoint(mock_reload, async_client):
    """Tests the reload endpoint orchestration safely via pipeline mocking."""
    mock_reload.return_value = {"status": "initialized", "incidents_loaded": 8173, "corridors_profiled": 45}
    
    response = await async_client.post("/api/data/reload")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "initialized"
    assert data["incidents_loaded"] == 8173
    mock_reload.assert_called_once()