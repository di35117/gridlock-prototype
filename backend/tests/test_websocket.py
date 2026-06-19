from fastapi.testclient import TestClient
from main import app
from modules.websockets.manager import notifier
import asyncio

client = TestClient(app)

def test_websocket_broadcast():
    test_alert = {"type": "CRITICAL_ALERT", "source": "Pytest", "message": "Testing the WS Pipeline"}

    with client.websocket_connect("/api/ws/dashboard") as websocket:
        assert len(notifier.active_connections) == 1
        
        # Simulate AI triggering an alert
        asyncio.run(notifier.broadcast_alert(test_alert))
        
        # Frontend receives it
        data = websocket.receive_json()
        assert data["type"] == "CRITICAL_ALERT"

    # Verifies server drops the connection cleanly
    assert len(notifier.active_connections) == 0