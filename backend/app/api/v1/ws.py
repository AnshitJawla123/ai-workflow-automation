from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services.jobs.ws_bus import bus

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/events")
async def events(ws: WebSocket):
    await bus.connect(ws)
    try:
        while True:
            # Keep the connection alive; ignore client messages
            await ws.receive_text()
    except WebSocketDisconnect:
        await bus.disconnect(ws)
    except Exception:
        await bus.disconnect(ws)
