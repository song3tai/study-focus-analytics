"""Simple WebSocket connection manager."""

from __future__ import annotations

import asyncio
import contextlib
import threading

from fastapi import WebSocket


class WebSocketManager:
    """Track connected sockets and broadcast JSON payloads."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        with self._lock:
            connections = list(self._connections)

        stale_connections: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)
            with contextlib.suppress(Exception):
                await connection.close()

    async def send_json(self, websocket: WebSocket, payload: dict) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            self.disconnect(websocket)
            with contextlib.suppress(Exception):
                await websocket.close()

    async def wait_for_disconnect(self, websocket: WebSocket) -> None:
        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            return
