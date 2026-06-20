import pytest
import asyncio
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from main import app
from modules.websockets.manager import notifier

# Standard TestClient is synchronous, which is perfect for WebSocket testing
client = TestClient(app)

# ─────────────────────────────────────────────────────────
# 1. Standard Connection & Keep-Alive Ping
# ─────────────────────────────────────────────────────────
def test_websocket_ping_pong():
    """Tests the connection lifecycle and the keep-alive ping-pong router logic."""
    notifier.active_connections.clear()
    
    with client.websocket_connect("/api/ws/dashboard") as websocket:
        # Verify the manager tracked the new connection
        assert len(notifier.active_connections) == 1
        
        # Test the keep-alive mechanism
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
        
    # Verify the manager cleanly unregistered the connection upon exit
    assert len(notifier.active_connections) == 0


# ─────────────────────────────────────────────────────────
# 2. JSON Broadcast Propagation
# ─────────────────────────────────────────────────────────
def test_websocket_broadcast():
    """Tests that a connected client successfully receives broadcasted alerts."""
    notifier.active_connections.clear()
    test_alert = {"type": "CRITICAL_ALERT", "source": "Pytest", "message": "Testing the WS Pipeline"}

    with client.websocket_connect("/api/ws/dashboard") as websocket:
        assert len(notifier.active_connections) == 1
        
        # Because TestClient is sync, we use asyncio.run to execute the async broadcast
        asyncio.run(notifier.broadcast_alert(test_alert))
        
        # Verify the payload was received intact
        data = websocket.receive_json()
        assert data["type"] == "CRITICAL_ALERT"
        assert data["message"] == "Testing the WS Pipeline"


# ─────────────────────────────────────────────────────────
# 3. Connection Cleanup on Network Failure
# ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_manager_disconnect_on_error():
    """Verifies the ConnectionManager cleans up broken sockets during a broadcast attempt."""
    notifier.active_connections.clear()
    
    # Create a mock websocket that simulates a dropped network (throws an error on send)
    broken_socket = AsyncMock()
    broken_socket.send_text.side_effect = Exception("Simulated socket drop")
    
    # Manually register the broken socket
    notifier.active_connections.append(broken_socket)
    assert len(notifier.active_connections) == 1
    
    # Attempt to broadcast. The manager should catch the error and remove the socket.
    await notifier.broadcast_alert({"msg": "This should trigger a cleanup"})
    
    # Verify the dead connection was successfully purged
    assert len(notifier.active_connections) == 0