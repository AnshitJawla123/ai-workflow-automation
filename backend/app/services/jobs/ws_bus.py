"""In-process WebSocket broadcast bus (no Redis needed)."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket

log = logging.getLogger("ws.bus")


class WebSocketBus:
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, event: str, payload: dict):
        msg = json.dumps({"event": event, "payload": payload}, default=str)
        async with self._lock:
            dead = []
            for ws in self._connections:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for d in dead:
                self._connections.discard(d)


bus = WebSocketBus()


def emit(event: str, payload: dict):
    """Fire-and-forget broadcast from sync code."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bus.broadcast(event, payload))
    except RuntimeError:
        # No running loop — schedule on new loop briefly
        asyncio.run(bus.broadcast(event, payload))
