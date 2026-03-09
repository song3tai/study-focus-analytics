"""Video reader module.

Encapsulates video loading and metadata access so future inputs
(camera, stream, RTSP) can reuse the same interface.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class VideoReader:
    """Wrapper around OpenCV VideoCapture with basic safety checks."""

    def __init__(self, input_path: Path) -> None:
        self.input_path = input_path
        self.cap = cv2.VideoCapture(str(input_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open video: {input_path}")

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        return self.cap.read()

    def fps(self) -> float:
        fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        return fps if fps > 0 else 30.0

    def frame_size(self) -> tuple[int, int]:
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            raise RuntimeError("Failed to read valid frame size from video.")
        return width, height

    def release(self) -> None:
        self.cap.release()
