from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from modules.websockets.manager import notifier

router = APIRouter(prefix="/api/ws", tags=["Real-Time Protocol"])

@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    The frontend React application connects to this endpoint.
    URL: ws://localhost:8000/api/ws/dashboard
    """
    await notifier.connect(websocket)
    try:
        while True:
            # We keep the connection alive. We don't expect the frontend to send 
            # much via WS (they use standard POST for actions), but we must listen.
            data = await websocket.receive_text()
            
            # Optional: Ping-pong to keep connection alive
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        notifier.disconnect(websocket)