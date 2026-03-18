"""Simple WebSocket connection manager."""

from __future__ import annotations

from fastapi import WebSocket


class WebSocketManager:
    """Track connected sockets and broadcast JSON payloads."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        for connection in list(self._connections):
            await connection.send_json(payload)

