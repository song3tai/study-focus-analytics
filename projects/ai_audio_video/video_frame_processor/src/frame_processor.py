"""Frame processing module for non-AI modes."""

from __future__ import annotations

import cv2
import numpy as np

SUPPORTED_MODES = ("original", "gray", "edge")


class FrameProcessor:
    """Frame processing logic for traditional modes."""

    def process_frame(self, frame: np.ndarray, mode: str) -> np.ndarray:
        """Process one frame by selected mode and return BGR output."""
        normalized_mode = mode.lower().strip()

        if normalized_mode == "original":
            return frame

        if normalized_mode == "gray":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        if normalized_mode == "edge":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, threshold1=80, threshold2=180)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        raise ValueError(
            f"Unsupported mode: {mode}. Supported modes: {', '.join(SUPPORTED_MODES)}"
        )
