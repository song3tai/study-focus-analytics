from __future__ import annotations

from pathlib import Path
import types

import cv2
import pytest

import src.io.video_reader as video_reader_module
from src.io.video_reader import CameraReader, RTSPReader, VideoReader, create_frame_source


class _FakeCapture:
    def __init__(self, opened: bool = True, fps: float = 0.0, width: int = 640, height: int = 480) -> None:
        self._opened = opened
        self._fps = fps
        self._width = width
        self._height = height
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self):
        return False, None

    def get(self, prop_id: int) -> float:
        if prop_id == cv2.CAP_PROP_FPS:
            return self._fps
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return self._width
        if prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return self._height
        return 0.0

    def release(self) -> None:
        self.released = True


def test_create_frame_source_returns_video_reader(monkeypatch) -> None:
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _path: _FakeCapture(opened=True))

    source = create_frame_source(
        input_path=Path("input/sample.mp4"),
        use_camera=False,
        camera_index=0,
        rtsp_url=None,
        rtsp_transport="tcp",
        fallback_fps=30.0,
    )

    assert isinstance(source, VideoReader)


def test_create_frame_source_returns_camera_reader(monkeypatch) -> None:
    monkeypatch.setattr(video_reader_module, "platform", types.SimpleNamespace(system=lambda: "Linux"))
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _index: _FakeCapture(opened=True))

    source = create_frame_source(
        input_path=None,
        use_camera=True,
        camera_index=2,
        rtsp_url=None,
        rtsp_transport="tcp",
        fallback_fps=25.0,
    )

    assert isinstance(source, CameraReader)
    assert source.is_live is True
    assert source.fps() == 25.0


def test_create_frame_source_returns_rtsp_reader(monkeypatch) -> None:
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _url: _FakeCapture(opened=True, fps=15.0))

    source = create_frame_source(
        input_path=None,
        use_camera=False,
        camera_index=0,
        rtsp_url="rtsp://172.29.160.1:8554/live",
        rtsp_transport="tcp",
        fallback_fps=25.0,
    )

    assert isinstance(source, RTSPReader)
    assert source.is_live is True
    assert source.fps() == 15.0
    assert source.transport == "tcp"
    assert source.requested_transport == "tcp"


def test_camera_reader_reports_clear_error(monkeypatch) -> None:
    fake_capture = _FakeCapture(opened=False)
    monkeypatch.setattr(video_reader_module, "platform", types.SimpleNamespace(system=lambda: "Linux"))
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _index: fake_capture)

    with pytest.raises(RuntimeError, match="failed to open camera: index=1. camera not available via backends \\[default\\]"):
        CameraReader(camera_index=1)

    assert fake_capture.released is True


def test_camera_reader_windows_falls_back_between_backends(monkeypatch) -> None:
    attempts: list[int | None] = []

    monkeypatch.setattr(video_reader_module, "platform", types.SimpleNamespace(system=lambda: "Windows"))
    monkeypatch.setattr(video_reader_module.cv2, "CAP_DSHOW", 700, raising=False)
    monkeypatch.setattr(video_reader_module.cv2, "CAP_MSMF", 1400, raising=False)

    def fake_capture_factory(index: int, backend: int | None = None) -> _FakeCapture:
        assert index == 0
        attempts.append(backend)
        if backend == 700:
            return _FakeCapture(opened=False)
        return _FakeCapture(opened=True)

    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", fake_capture_factory)

    reader = CameraReader(camera_index=0)

    assert attempts == [700, 1400]
    assert reader.backend_name == "msmf"


def test_rtsp_reader_reports_clear_error(monkeypatch) -> None:
    fake_capture = _FakeCapture(opened=False)
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _url: fake_capture)

    with pytest.raises(
        RuntimeError,
        match="failed to open rtsp stream: rtsp://192.168.3.3:8554/live \\(requested=auto, tried=\\[tcp, udp\\]\\)",
    ):
        RTSPReader(stream_url="rtsp://192.168.3.3:8554/live")

    assert fake_capture.released is True


def test_rtsp_reader_sets_ffmpeg_transport_option_temporarily(monkeypatch) -> None:
    observed_option = None

    def fake_capture_factory(_url: str) -> _FakeCapture:
        nonlocal observed_option
        observed_option = __import__("os").environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
        return _FakeCapture(opened=True)

    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", fake_capture_factory)

    RTSPReader(stream_url="rtsp://192.168.3.3:8554/live", transport="tcp")

    assert observed_option == "rtsp_transport;tcp"
    assert __import__("os").environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS") is None


def test_rtsp_reader_auto_falls_back_to_udp(monkeypatch) -> None:
    attempts: list[str | None] = []

    def fake_capture_factory(_url: str) -> _FakeCapture:
        transport = __import__("os").environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
        attempts.append(transport)
        if transport == "rtsp_transport;tcp":
            return _FakeCapture(opened=False)
        return _FakeCapture(opened=True, fps=20.0)

    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", fake_capture_factory)

    reader = RTSPReader(stream_url="rtsp://192.168.3.3:8554/live", transport="auto")

    assert attempts == ["rtsp_transport;tcp", "rtsp_transport;udp"]
    assert reader.transport == "udp"


def test_rtsp_reader_reconnect_reopens_stream(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_capture_factory(_url: str) -> _FakeCapture:
        calls["count"] += 1
        return _FakeCapture(opened=True)

    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", fake_capture_factory)

    reader = RTSPReader(stream_url="rtsp://192.168.3.3:8554/live", transport="udp")

    assert reader.reconnect() is True
    assert calls["count"] == 2


def test_video_reader_uses_fallback_fps(monkeypatch) -> None:
    monkeypatch.setattr("src.io.video_reader.cv2.VideoCapture", lambda _path: _FakeCapture(opened=True, fps=0.0))

    reader = VideoReader(Path("input/sample.mp4"), fallback_fps=29.97)

    assert reader.fps() == 29.97
