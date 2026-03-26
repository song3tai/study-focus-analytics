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


class _FakeSessionResult:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


class _FakeService:
    def __init__(self) -> None:
        self.websocket_manager = _FakeWebSocketManager()
        self._stop_result = _FakeSessionResult(
            {
                "session_id": "realtime-session-1",
                "source_type": "camera",
                "source_name": "camera:0",
                "analysis_mode": "realtime",
                "summary": {
                    "total_duration_sec": 8.0,
                    "total_present_duration_sec": 6.0,
                    "total_away_duration_sec": 2.0,
                    "total_studying_duration_sec": 4.0,
                    "away_count": 1,
                    "average_focus_score": 0.61,
                    "max_focus_score": 0.78,
                    "min_focus_score": 0.21,
                    "focus_samples": 80,
                },
                "events": [
                    {
                        "event_type": "away_started",
                        "timestamp": 2.5,
                        "frame_id": 75,
                        "state_before": "present",
                        "state_after": "away",
                        "message": "user left the study/work area",
                        "payload": {},
                    }
                ],
                "timeline": [],
                "duration_sec": 8.0,
            }
        )

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

    def run_analysis(self, *, source_type: str, source: str, mode: str) -> _FakeSessionResult:
        return _FakeSessionResult(
            {
                "session_id": "session-1",
                "source_type": "file",
                "source_name": source,
                "analysis_mode": mode,
                "summary": {
                    "total_duration_sec": 12.0,
                    "total_present_duration_sec": 10.0,
                    "total_away_duration_sec": 2.0,
                    "total_studying_duration_sec": 7.0,
                    "away_count": 1,
                    "average_focus_score": 0.64,
                    "max_focus_score": 0.8,
                    "min_focus_score": 0.2,
                    "focus_samples": 120,
                },
                "events": [
                    {
                        "event_type": "away_started",
                        "timestamp": 3.0,
                        "frame_id": 90,
                        "state_before": "present",
                        "state_after": "away",
                        "message": "user left the study/work area",
                        "payload": {},
                    }
                ],
                "timeline": [],
                "duration_sec": 12.0,
            }
        )

    def stop(self):
        return True, "analysis session stopped", self._stop_result

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


def test_session_result_page_is_available() -> None:
    client = TestClient(create_app(service=_FakeService()))

    response = client.get("/static/session_result.html")

    assert response.status_code == 200
    assert "Session Result | Study Focus Analytics" in response.text


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


def test_analysis_run_returns_session_result() -> None:
    client = TestClient(create_app(service=_FakeService()))

    response = client.post(
        "/analysis/run",
        json={
            "source_type": "video_file",
            "source": "input/sample.mp4",
            "mode": "fast",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "fast analysis completed"
    assert payload["data"]["analysis_mode"] == "fast"
    assert payload["data"]["source_type"] == "file"
    assert payload["data"]["summary"]["total_duration_sec"] == 12.0
    assert payload["data"]["timeline"] == []
    assert payload["data"]["events"][0]["event_type"] == "away_started"


def test_analysis_stop_returns_session_result() -> None:
    client = TestClient(create_app(service=_FakeService()))

    response = client.post("/analysis/stop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["session_state"] == "idle"
    assert payload["session_result"]["analysis_mode"] == "realtime"
    assert payload["session_result"]["summary"]["total_duration_sec"] == 8.0
    assert payload["session_result"]["events"][0]["event_type"] == "away_started"


