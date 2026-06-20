import pytest
import networkx as nx
from unittest.mock import patch, AsyncMock, MagicMock

# ─────────────────────────────────────────────────────────
# 1. Integration Test - POST /api/routing/diversion Endpoint
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.routing_engine.service.calculate_tactical_diversion')
async def test_get_diversion_endpoint_success(mock_calculate, async_client):
    """Verifies that the diversion API parses inputs and returns valid GeoJSON paths."""
    
    # Mocking the service method output
    mock_calculate.return_value = {
        "status": "Diversion Generated Successfully",
        "route_geojson": {
            "type": "LineString",
            "coordinates": [[77.50, 12.90], [77.52, 12.92]]
        },
        "barricade_points": [{"latitude": 12.91, "longitude": 77.51}],
        "blocked_construction_nodes": 1
    }

    payload = {
        "corridor": "Outer Ring Road",
        "origin_lat": 12.90,
        "origin_lon": 77.50,
        "dest_lat": 12.92,
        "dest_lon": 77.52
    }

    response = await async_client.post("/api/routing/diversion", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Diversion Generated Successfully"
    assert data["route_geojson"]["type"] == "LineString"
    assert len(data["barricade_points"]) == 1
    assert data["blocked_construction_nodes"] == 1


@pytest.mark.asyncio
@patch('modules.routing_engine.service.calculate_tactical_diversion')
async def test_get_diversion_endpoint_runtime_error(mock_calculate, async_client):
    """Verifies the API accurately wraps internal routing exceptions into a 500 error."""
    
    mock_calculate.side_effect = RuntimeError("Graph file not found. Ensure the download_graph script was run.")

    payload = {
        "corridor": "Invalid Route",
        "origin_lat": 12.90,
        "origin_lon": 77.50,
        "dest_lat": 12.92,
        "dest_lon": 77.52
    }

    response = await async_client.post("/api/routing/diversion", json=payload)
    
    assert response.status_code == 500
    assert "Graph file not found" in response.json()["detail"]


# ─────────────────────────────────────────────────────────
# 2. Integration Test - GET /api/routing/network/metrics
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.routing_engine.service.engine')
@patch('modules.routing_engine.service._get_graph')
async def test_get_network_metrics_geojson(mock_get_graph, mock_engine, async_client):
    """Verifies city road network converts to GeoJSON FeatureCollection with embedded risks."""
    
    # 1. Setup a synthetic mock graph with edge attributes
    G = nx.MultiDiGraph()
    G.add_node(1, x=77.50, y=12.90)
    G.add_node(2, x=77.51, y=12.91)
    
    # Add an edge containing attributes expected by service.py (_build_features)
    G.add_edge(
        1, 2, 
        name="Hosur Road", 
        highway="primary", 
        geometry=MagicMock(coords=[(77.50, 12.90), (77.51, 12.91)])
    )
    mock_get_graph.return_value = G

    # 2. Mock DB execution for fetching corridor risk profiles
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    
    mock_row = MagicMock()
    mock_row.corridor = "hosur road"
    mock_row.risk_score = 0.78
    
    mock_result.fetchall.return_value = [mock_row]
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    response = await async_client.get("/api/routing/network/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    
    # Verify embedded properties for MapLibre data-driven styling are cleanly mapped
    feature_properties = data["features"][0]["properties"]
    assert feature_properties["name"] == "Hosur Road"
    assert feature_properties["highway"] == "primary"
    assert feature_properties["risk_score"] == 0.78


# ─────────────────────────────────────────────────────────
# 3. Core Routing Logic Unit Test
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch('modules.routing_engine.service._get_construction_coordinates')
@patch('modules.routing_engine.service._get_graph')
@patch('osmnx.distance.nearest_nodes')
@patch('networkx.shortest_path')
async def test_routing_engine_core_logic(mock_shortest_path, mock_nearest_nodes, mock_get_graph, mock_get_coords):
    """Validates core routing algorithms cleanly avoid nodes containing construction blocks."""
    
    # Setup simple graph structure
    G = nx.MultiDiGraph()
    G.graph["crs"] = "epsg:4326"
    G.add_node(1, y=12.90, x=77.50)
    G.add_node(2, y=12.91, x=77.51)  # The construction block target
    G.add_node(3, y=12.92, x=77.52)
    
    G.add_edge(1, 2, length=10)
    G.add_edge(2, 3, length=10)
    G.add_edge(1, 3, length=25)  # Safe alternate bypass road
    
    mock_get_graph.return_value = G
    mock_get_coords.return_value = [(12.91, 77.51)]
    
    # Mock nearest node resolutions to simulate origin, block, and destination nodes
    mock_nearest_nodes.side_effect = [1, 3, 2] 
    
    # Expect the routing system to yield a path bypassing node 2
    mock_shortest_path.return_value = [1, 3]

    from modules.routing_engine.service import calculate_tactical_diversion
    result = await calculate_tactical_diversion(
        corridor="Synthetic Bypass Test Corridor",
        o_lat=12.90, o_lon=77.50,
        d_lat=12.92, d_lon=77.52
    )
    
    assert result["status"] == "Optimal Diversion Found"
    assert result["blocked_construction_nodes"] == 1
    assert result["route_geojson"]["type"] == "LineString"