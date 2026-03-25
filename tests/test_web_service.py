from __future__ import annotations

import src.web.service as web_service_module
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


def test_start_clears_stale_preview(monkeypatch) -> None:
    monkeypatch.setattr(web_service_module.threading, "Thread", _DummyThread)

    service = AnalysisWebService()
    service._latest_preview_jpeg = b"stale-preview"

    success, _message = service.start(source_type="video_file", source="input/sample.mp4", debug=False)

    assert success is True
    assert service.get_latest_preview_jpeg() is None


def test_stop_clears_stale_preview() -> None:
    service = AnalysisWebService()
    service._running = True
    service._session_state = "running"
    service._latest_preview_jpeg = b"stale-preview"

    success, _message = service.stop()

    assert success is True
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

    success, _message = service.stop()

    assert success is True
    assert reader.released is True
