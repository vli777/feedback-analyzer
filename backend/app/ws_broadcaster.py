"""
WebSocket broadcaster for pushing events to connected frontend clients.
"""

import asyncio
import json
import logging

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class Broadcaster:
    """Manages a set of connected frontend WebSocket clients and broadcasts events."""

    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("Frontend WS client connected, total=%d", len(self._clients))

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        logger.info("Frontend WS client disconnected, total=%d", len(self._clients))

    async def broadcast(self, event: dict):
        """Send an event dict to all connected clients. Dead clients are auto-removed."""
        message = json.dumps(event)
        dead: set[WebSocket] = set()

        async with self._lock:
            clients = set(self._clients)

        for ws in clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                self._clients -= dead
            logger.info("Removed %d dead WS clients", len(dead))

    @property
    def client_count(self) -> int:
        return len(self._clients)
