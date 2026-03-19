"""YOLOv8 detector with structured outputs for the analysis pipeline."""

from __future__ import annotations

import os
from time import perf_counter
from typing import Any

import cv2
import numpy as np

from src.core.models import BBox, Detection, DetectionResult
from src.utils import ensure_dir, project_root


class AIDetector:
    """Load YOLO once and return structured detections."""

    def __init__(self, model_name: str, conf_threshold: float = 0.35) -> None:
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self._model: Any | None = None

    def load_model(self) -> None:
        if self._model is not None:
            return

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

    def detect_frame(
        self,
        frame: np.ndarray,
        *,
        frame_index: int = 0,
        timestamp_seconds: float = 0.0,
    ) -> DetectionResult:
        """Run model inference and return structured detection objects."""
        self.load_model()
        assert self._model is not None

        started_at = perf_counter()
        results = self._model.predict(frame, conf=self.conf_threshold, verbose=False)
        inference_ms = (perf_counter() - started_at) * 1000.0

        if not results:
            return DetectionResult(
                frame_id=frame_index,
                timestamp=timestamp_seconds,
                detections=[],
                inference_ms=inference_ms,
                model_name=self.model_name,
            )

        raw_result = results[0]
        detections = self._to_detections(raw_result)
        return DetectionResult(
            frame_id=frame_index,
            timestamp=timestamp_seconds,
            detections=detections,
            inference_ms=inference_ms,
            model_name=self.model_name,
        )

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Backward-compatible annotated-frame path for legacy preview mode."""
        detection_result = self.detect_frame(frame)
        return self.annotate(frame=frame, detection_result=detection_result)

    def annotate(self, frame: np.ndarray, detection_result: DetectionResult) -> np.ndarray:
        """Render simple bounding boxes and labels onto a BGR frame."""
        annotated = frame.copy()
        for detection in detection_result.detections:
            x1, y1, x2, y2 = detection.bbox.x1, detection.bbox.y1, detection.bbox.x2, detection.bbox.y2
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 0), 2)
            label = f"{detection.label} {detection.confidence:.2f}"
            cv2.putText(
                annotated,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 0),
                2,
                cv2.LINE_AA,
            )
        return annotated

    @staticmethod
    def _to_detections(raw_result: Any) -> list[Detection]:
        boxes = getattr(raw_result, "boxes", None)
        if boxes is None:
            return []

        names = getattr(raw_result, "names", {})
        xyxy_values = getattr(boxes, "xyxy", [])
        conf_values = getattr(boxes, "conf", [])
        cls_values = getattr(boxes, "cls", [])

        detections: list[Detection] = []
        for xyxy, conf_value, cls_value in zip(xyxy_values, conf_values, cls_values):
            coords = xyxy.tolist() if hasattr(xyxy, "tolist") else list(xyxy)
            class_id = int(cls_value.item() if hasattr(cls_value, "item") else cls_value)
            confidence = float(conf_value.item() if hasattr(conf_value, "item") else conf_value)
            label = str(names.get(class_id, class_id))
            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=label,
                    confidence=confidence,
                    bbox=BBox(
                        x1=int(coords[0]),
                        y1=int(coords[1]),
                        x2=int(coords[2]),
                        y2=int(coords[3]),
                    ),
                )
            )
        return detections
