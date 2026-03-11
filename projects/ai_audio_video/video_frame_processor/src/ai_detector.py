"""YOLOv8 detector module for frame-level object detection."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from utils import ensure_dir, project_root


class AIDetector:
    """Load YOLOv8 once and run per-frame inference."""

    def __init__(self, model_name: str, conf_threshold: float = 0.35) -> None:
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self._model: Any | None = None

    def load_model(self) -> None:
        """Load YOLO model once (lazy initialization)."""
        if self._model is not None:
            return

        # Keep ultralytics runtime files inside project-writable space.
        config_dir = project_root() / ".ultralytics"
        ensure_dir(config_dir)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
        os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(config_dir))

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Install dependencies with: pip install -r requirements.txt"
            ) from exc

        self._model = YOLO(self.model_name)

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Run detection and return an annotated BGR frame."""
        self.load_model()
        assert self._model is not None

        results = self._model.predict(frame, conf=self.conf_threshold, verbose=False)
        if not results:
            return frame

        return results[0].plot()
