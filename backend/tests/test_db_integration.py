import pytest
from sqlalchemy import text
from database import engine

@pytest.mark.asyncio
async def test_real_database_surge_logic(async_client):
    """
    Tier 1 Integration Test:
    Injects real data into the Postgres container and ensures the raw SQL 
    in the Surge Detector mathematically calculates the Z-Score correctly.
    """
    
    # 1. SEED THE TEMPORARY DATABASE
    # We manually insert a baseline profile for a test road
    insert_query = text("""
        INSERT INTO corridor_risk_profiles 
        (corridor, avg_hourly_baseline, std_hourly_baseline, last_updated)
        VALUES ('Test Integration Road', 10.0, 2.0, NOW())
    """)
    
    async with engine.begin() as conn:
        await conn.execute(insert_query)

    # 2. EXECUTE THE REAL API HIT
    # 14 incidents against a mean of 10 and std of 2 should result in a Z-score of 2.0
    payload = {
        "corridor": "Test Integration Road",
        "current_hourly_incidents": 14
    }
    
    response = await async_client.post("/api/surge/check", json=payload)
    
    # 3. ASSERT REAL SQL EXECUTION
    assert response.status_code == 200
    data = response.json()
    
    assert data["corridor"] == "Test Integration Road"
    assert data["baseline_mean"] == 10.0
    assert data["baseline_std"] == 2.0
    assert data["z_score"] == 2.0
    assert data["is_surge_detected"] is False # Must be > 2.0 to trigger