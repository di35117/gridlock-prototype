"""
Real-Time Connection Manager for the C3 Dashboard.
Holds open WebSocket connections and broadcasts instant JSON payloads
to all connected React clients when an anomaly is detected.
"""

import logging
import json
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # List of active React clients currently viewing the dashboard
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WebSocket] Dashboard connected. Active viewers: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WebSocket] Dashboard disconnected. Active viewers: {len(self.active_connections)}")

    async def broadcast_alert(self, payload: dict):
        """
        Pushes a JSON payload to every connected dashboard instantly.
        """
        message = json.dumps(payload)
        # FIX: Iterate over a copy of the list using .copy() to prevent RuntimeError during drops
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"[WebSocket] Failed to send message to a client: {e}")
                self.disconnect(connection)

# Global singleton instance so any module can import it and broadcast
notifier = ConnectionManager()