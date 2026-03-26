from __future__ import annotations

import src.web.service as web_service_module
from src.core.enums import AnalysisMode, SourceType
from src.core.models import SessionResult
from src.web.service import AnalysisWebService


class _DummyThread:
    def __init__(self, target=None, kwargs=None, daemon=None, name=None) -> None:
        self._alive = False

    def start(self) -> None:
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout=None) -> None:
        return None


def _build_result() -> SessionResult:
    return SessionResult.empty(
        session_id="session-1",
        source_type=SourceType.CAMERA,
        source_name="camera:0",
        analysis_mode=AnalysisMode.REALTIME,
    )


def test_start_clears_stale_preview_and_last_session_result(monkeypatch) -> None:
    monkeypatch.setattr(web_service_module.threading, "Thread", _DummyThread)

    service = AnalysisWebService()
    service._latest_preview_jpeg = b"stale-preview"
    service._last_session_result = _build_result()

    success, _message = service.start(source_type="video_file", source="input/sample.mp4", debug=False)

    assert success is True
    assert service.get_latest_preview_jpeg() is None
    assert service.get_last_session_result() is None


def test_stop_clears_stale_preview() -> None:
    service = AnalysisWebService()
    service._running = True
    service._session_state = "running"
    service._latest_preview_jpeg = b"stale-preview"

    success, _message, session_result = service.stop()

    assert success is True
    assert session_result is None
    assert service.get_latest_preview_jpeg() is None


def test_stop_releases_active_reader() -> None:
    class _Reader:
        def __init__(self) -> None:
            self.released = False

        def release(self) -> None:
            self.released = True

    reader = _Reader()
    service = AnalysisWebService()
    service._running = True
    service._session_state = "running"
    service._active_reader = reader

    success, _message, _session_result = service.stop()

    assert success is True
    assert reader.released is True


def test_stop_returns_last_session_result() -> None:
    service = AnalysisWebService()
    expected = _build_result()
    service._running = True
    service._session_state = "running"
    service._last_session_result = expected

    success, _message, session_result = service.stop()

    assert success is True
    assert session_result is expected


def test_run_analysis_rejects_non_fast_mode() -> None:
    service = AnalysisWebService()

    try:
        service.run_analysis(source_type="video_file", source="input/sample.mp4", mode="realtime")
    except ValueError as exc:
        assert "only fast mode" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-fast mode")
