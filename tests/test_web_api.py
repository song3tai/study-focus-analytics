from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from src.web.api import create_app


class _FakeWebSocketManager:
    async def connect(self, websocket):  # pragma: no cover - websocket route not exercised here
        return None

    def disconnect(self, websocket):  # pragma: no cover - websocket route not exercised here
        return None

    async def send_json(self, websocket, payload):  # pragma: no cover
        return None

    async def wait_for_disconnect(self, websocket):  # pragma: no cover
        return None

    async def broadcast_json(self, payload):  # pragma: no cover
        return None


class _FakeService:
    def __init__(self) -> None:
        self.websocket_manager = _FakeWebSocketManager()

    def bind_event_loop(self, loop) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def get_status_payload(self) -> dict[str, Any]:
        return {
            "running": False,
            "session_state": "idle",
            "source_type": None,
            "source": None,
            "started_at": None,
            "has_latest_result": False,
            "last_frame_id": None,
            "last_timestamp": None,
            "last_error": None,
        }

    def start(self, *, source_type: str, source: str | None, debug: bool = False) -> tuple[bool, str]:
        return True, "analysis session starting"

    def stop(self) -> tuple[bool, str]:
        return True, "analysis session stopped"

    def get_latest_result(self):
        return None

    def get_latest_summary(self):
        return None

    def get_current_timestamp(self) -> str:
        return "2026-03-24T00:00:00+00:00"

    def preview_stream(self):
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nfake-jpeg\r\n"


def test_dashboard_index_serves_html() -> None:
    client = TestClient(create_app(service=_FakeService()))

    response = client.get("/")

    assert response.status_code == 200
    assert "Study Focus Analytics Dashboard" in response.text


def test_analysis_video_stream_is_available() -> None:
    client = TestClient(create_app(service=_FakeService()))

    with client.stream("GET", "/analysis/video") as response:
        first_chunk = next(response.iter_bytes())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"--frame" in first_chunk


def test_analysis_status_matches_schema() -> None:
    client = TestClient(create_app(service=_FakeService()))

    response = client.get("/analysis/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["running"] is False
    assert payload["session_state"] == "idle"
