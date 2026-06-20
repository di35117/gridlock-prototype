import pytest
from sqlalchemy import text
from database import engine

@pytest.mark.asyncio
async def test_real_database_surge_logic(async_client):
    insert_query = text("""
        INSERT INTO corridor_risk_profiles 
        (corridor, avg_hourly_baseline, std_hourly_baseline)
        VALUES ('Test Integration Road', 10.0, 2.0)
    """)
    cleanup_query = text("DELETE FROM corridor_risk_profiles WHERE corridor = 'Test Integration Road'")
    
    async with engine.begin() as conn:
        await conn.execute(insert_query)

    try:
        # Changed from 14 to 15 to ensure Z-Score is 2.5 (strictly > 2.0)
        payload = {
            "corridor": "Test Integration Road",
            "current_hourly_incidents": 15 
        }
        
        response = await async_client.post("/api/surge/check", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["corridor"] == "Test Integration Road"
        assert data["baseline_mean"] == 10.0
        assert data["baseline_std"] == 2.0
        assert data["z_score"] == 2.5 
        assert data["is_surge_detected"] == True
        
    finally:
        async with engine.begin() as conn:
            await conn.execute(cleanup_query)