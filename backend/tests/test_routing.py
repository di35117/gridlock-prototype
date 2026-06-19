import pytest
from unittest.mock import patch

@pytest.mark.asyncio
@patch('modules.routing_engine.service.calculate_diversion')
async def test_routing_engine_endpoint(mock_diversion, async_client):
    mock_diversion.return_value = {
        "route_geojson": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[77.5, 12.9], [77.6, 12.9]]}},
        "barricade_points": [{"lat": 12.91, "lon": 77.51}],
        "blocked_nodes": 3
    }

    response = await async_client.post("/api/routing/diversion", json={
        "corridor": "Silk Board", "latitude": 12.91, "longitude": 77.51
    })
    
    assert response.status_code == 200
    assert "route_geojson" in response.json()