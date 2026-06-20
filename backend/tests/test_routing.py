import pytest
import networkx as nx
from unittest.mock import patch
from modules.routing_engine.service import calculate_tactical_diversion

@pytest.mark.asyncio
@patch('modules.routing_engine.service._get_construction_coordinates')
@patch('modules.routing_engine.service._get_graph')
async def test_routing_engine_core_logic(mock_get_graph, mock_get_coords):
    # Synthetic Graph Creation
    G = nx.MultiDiGraph()
    # FIX: OSMnx strictly requires a CRS (Coordinate Reference System) to be set
    G.graph["crs"] = "epsg:4326" 
    
    G.add_node(1, y=12.90, x=77.50)
    G.add_node(2, y=12.91, x=77.51) # Blocked node
    G.add_node(3, y=12.92, x=77.52)
    G.add_edge(1, 2, length=10)
    G.add_edge(2, 3, length=10)
    G.add_edge(1, 3, length=25) # Alternate route
    
    mock_get_graph.return_value = G
    mock_get_coords.return_value = [(12.91, 77.51)]

    result = await calculate_tactical_diversion(
        corridor="Synthetic Road",
        o_lat=12.90, o_lon=77.50,
        d_lat=12.92, d_lon=77.52
    )

    assert result["status"] == "Optimal Diversion Found"
    assert result["blocked_construction_nodes"] == 1
    coords = result["route_geojson"]["geometry"]["coordinates"]
    assert len(coords) == 2 
    assert result["barricade_points"][0]["lat"] == 12.91