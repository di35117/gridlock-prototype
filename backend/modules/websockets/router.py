from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from modules.websockets.manager import notifier
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def handle_websocket(websocket: WebSocket):
    """Core logic to handle the handshake and keep the connection alive."""
    await notifier.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        notifier.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        notifier.disconnect(websocket)

@router.websocket("/api/stream/live")
async def websocket_endpoint_live(websocket: WebSocket, token: str = None):
    """Primary WebSocket endpoint."""
    await handle_websocket(websocket)

@router.websocket("/api/ws/dashboard")
async def websocket_endpoint_dashboard(websocket: WebSocket, token: str = None):
    """Alias endpoint to prevent 403 errors from older frontend clients."""
    await handle_websocket(websocket)