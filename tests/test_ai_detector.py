from __future__ import annotations

import types

import numpy as np

import src.inference.ai_detector as ai_detector_module
from src.inference.ai_detector import AIDetector


class _FakeYOLO:
    init_count = 0

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        _FakeYOLO.init_count += 1

    def predict(self, frame: np.ndarray, conf: float, verbose: bool):
        assert conf == 0.5
        assert verbose is False
        return [
            types.SimpleNamespace(
                names={0: "person"},
                boxes=types.SimpleNamespace(
                    xyxy=[np.array([1, 2, 5, 6], dtype=float)],
                    conf=[np.array(0.9, dtype=float)],
                    cls=[np.array(0.0, dtype=float)],
                ),
            )
        ]


def test_detector_loads_model_once_and_returns_structured_detection(monkeypatch) -> None:
    fake_ultralytics = types.SimpleNamespace(YOLO=_FakeYOLO)
    monkeypatch.setitem(__import__("sys").modules, "ultralytics", fake_ultralytics)
    monkeypatch.setattr(ai_detector_module, "project_root", lambda: __import__("pathlib").Path("."))
    monkeypatch.setattr(ai_detector_module, "ensure_dir", lambda _path: None)

    _FakeYOLO.init_count = 0
    detector = AIDetector(model_name="yolov8n.pt", conf_threshold=0.5)

    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    out1 = detector.detect_frame(frame, frame_index=3, timestamp_seconds=1.25)
    out2 = detector.detect_frame(frame, frame_index=4, timestamp_seconds=1.5)

    assert _FakeYOLO.init_count == 1
    assert out1.frame_index == 3
    assert out1.timestamp_seconds == 1.25
    assert len(out1.detections) == 1
    assert out1.detections[0].label == "person"
    assert out1.detections[0].bbox.x1 == 1
    assert len(out2.detections) == 1
