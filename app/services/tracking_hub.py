import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class TrackingHub:
    """
    In-memory live tracking broadcaster.

    Each request has a set of connected dashboard WebSockets.
    When a donor location changes, the location payload is broadcast
    to every dashboard watching that request.
    """

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, request_id: str, websocket: WebSocket):
        await websocket.accept()

        async with self._lock:
            self._connections.setdefault(request_id, set()).add(websocket)

    async def disconnect(self, request_id: str, websocket: WebSocket):
        async with self._lock:
            connections = self._connections.get(request_id)

            if not connections:
                return

            connections.discard(websocket)

            if not connections:
                self._connections.pop(request_id, None)

    async def broadcast(self, request_id: str, payload: dict):
        async with self._lock:
            connections = list(
                self._connections.get(request_id, set())
            )

        if not connections:
            return

        dead = []

        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)

        if dead:
            async with self._lock:
                current = self._connections.get(request_id, set())

                for websocket in dead:
                    current.discard(websocket)

                if not current:
                    self._connections.pop(request_id, None)


tracking_hub = TrackingHub()
