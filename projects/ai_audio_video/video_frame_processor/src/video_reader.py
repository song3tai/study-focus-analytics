"""Input source abstractions backed by OpenCV VideoCapture."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path

import cv2
import numpy as np


class FrameSource(ABC):
    """Common interface for frame-producing inputs."""

    @abstractmethod
    def is_opened(self) -> bool:
        """Return whether underlying source is available."""

    @abstractmethod
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Read next frame."""

    @abstractmethod
    def fps(self) -> float:
        """Return source FPS or a sensible fallback."""

    @abstractmethod
    def frame_size(self) -> tuple[int, int]:
        """Return source frame size."""

    @abstractmethod
    def release(self) -> None:
        """Release underlying resources."""

    @property
    @abstractmethod
    def is_live(self) -> bool:
        """Return whether source is a live stream."""

    def reconnect(self) -> bool:
        """Try to reconnect a live source. Non-live sources return False."""
        return False


class OpenCVFrameSource(FrameSource):
    """Shared OpenCV VideoCapture wrapper with metadata helpers."""

    def __init__(self, capture: cv2.VideoCapture, source_label: str, fallback_fps: float = 30.0) -> None:
        self.cap = capture
        self.source_label = source_label
        self.fallback_fps = fallback_fps
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open source: {source_label}")

    @property
    def is_live(self) -> bool:
        return False

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        return self.cap.read()

    def fps(self) -> float:
        fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        return fps if fps > 0 else self.fallback_fps

    def frame_size(self) -> tuple[int, int]:
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            raise RuntimeError(f"Failed to read valid frame size from source: {self.source_label}")
        return width, height

    def release(self) -> None:
        self.cap.release()


class VideoReader(OpenCVFrameSource):
    """File-backed frame reader."""

    def __init__(self, input_path: Path, fallback_fps: float = 30.0) -> None:
        self.input_path = input_path
        super().__init__(
            capture=cv2.VideoCapture(str(input_path)),
            source_label=str(input_path),
            fallback_fps=fallback_fps,
        )


class CameraReader(OpenCVFrameSource):
    """Camera-backed frame reader for real-time capture."""

    def __init__(self, camera_index: int = 0, fallback_fps: float = 30.0) -> None:
        self.camera_index = camera_index
        capture = cv2.VideoCapture(camera_index)
        try:
            super().__init__(
                capture=capture,
                source_label=f"camera:{camera_index}",
                fallback_fps=fallback_fps,
            )
        except RuntimeError as exc:
            capture.release()
            raise RuntimeError(
                f"failed to open camera: index={camera_index}. camera not available"
            ) from exc

    @property
    def is_live(self) -> bool:
        return True


class RTSPReader(OpenCVFrameSource):
    """RTSP-backed frame reader for network video streams."""

    def __init__(self, stream_url: str, transport: str = "auto", fallback_fps: float = 30.0) -> None:
        self.stream_url = stream_url
        self.requested_transport = transport
        self.transport = transport
        capture, resolved_transport = self._open_with_fallback(stream_url=stream_url, transport=transport)
        self.transport = resolved_transport
        super().__init__(
            capture=capture,
            source_label=stream_url,
            fallback_fps=fallback_fps,
        )

    @property
    def is_live(self) -> bool:
        return True

    def reconnect(self) -> bool:
        self.release()
        try:
            capture, resolved_transport = self._open_with_fallback(
                stream_url=self.stream_url,
                transport=self.requested_transport,
            )
        except RuntimeError:
            return False
        self.cap = capture
        self.transport = resolved_transport
        return True

    @staticmethod
    def _open_capture(stream_url: str, transport: str) -> cv2.VideoCapture:
        env_key = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
        previous_value = os.environ.get(env_key)
        try:
            os.environ[env_key] = f"rtsp_transport;{transport}"
            return cv2.VideoCapture(stream_url)
        finally:
            if previous_value is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = previous_value

    @classmethod
    def _open_with_fallback(cls, stream_url: str, transport: str) -> tuple[cv2.VideoCapture, str]:
        attempted_transports = cls._transport_candidates(transport)
        for candidate in attempted_transports:
            capture = cls._open_capture(stream_url=stream_url, transport=candidate)
            if capture.isOpened():
                return capture, candidate
            capture.release()

        attempted = ", ".join(attempted_transports)
        raise RuntimeError(
            f"failed to open rtsp stream: {stream_url} (requested={transport}, tried=[{attempted}])"
        )

    @staticmethod
    def _transport_candidates(transport: str) -> tuple[str, ...]:
        if transport == "auto":
            return ("tcp", "udp")
        return (transport,)


def create_frame_source(
    *,
    input_path: Path | None,
    use_camera: bool,
    camera_index: int,
    rtsp_url: str | None,
    rtsp_transport: str,
    fallback_fps: float,
) -> FrameSource:
    """Build a frame source from CLI/runtime configuration."""
    if rtsp_url:
        return RTSPReader(
            stream_url=rtsp_url,
            transport=rtsp_transport,
            fallback_fps=fallback_fps,
        )
    if use_camera:
        return CameraReader(camera_index=camera_index, fallback_fps=fallback_fps)
    if input_path is None:
        raise ValueError("input_path is required when neither camera nor rtsp mode is enabled")
    return VideoReader(input_path=input_path, fallback_fps=fallback_fps)
