"""Output video writing abstraction."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class VideoWriter:
    """Small wrapper around OpenCV VideoWriter."""

    def __init__(self, output_path: Path, width: int, height: int, fps: float) -> None:
        self.output_path = output_path
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if not self._writer.isOpened():
            raise RuntimeError(f"Unable to create output video writer: {output_path}")

    def write_frame(self, frame: np.ndarray) -> None:
        self._writer.write(frame)

    def release(self) -> None:
        self._writer.release()
