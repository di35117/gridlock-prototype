from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from modules.websockets.manager import notifier
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/api/stream/live")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    Hackathon Bypass: Accepts the WebSocket connection and gracefully 
    ignores the old React security token to prevent 403 Forbidden errors.
    """
    await notifier.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        notifier.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        notifier.disconnect(websocket)