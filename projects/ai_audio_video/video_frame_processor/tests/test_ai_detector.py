from __future__ import annotations

import types

import numpy as np

import ai_detector as ai_detector_module
from ai_detector import AIDetector


class _FakeResult:
    def __init__(self, frame: np.ndarray) -> None:
        self._frame = frame

    def plot(self) -> np.ndarray:
        return self._frame + 7


class _FakeYOLO:
    init_count = 0

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        _FakeYOLO.init_count += 1

    def predict(self, frame: np.ndarray, conf: float, verbose: bool):
        assert conf == 0.5
        assert verbose is False
        return [_FakeResult(frame)]


def test_detector_loads_model_once_and_returns_annotated_frame(monkeypatch) -> None:
    fake_ultralytics = types.SimpleNamespace(YOLO=_FakeYOLO)
    monkeypatch.setitem(__import__("sys").modules, "ultralytics", fake_ultralytics)
    monkeypatch.setattr(ai_detector_module, "project_root", lambda: __import__("pathlib").Path("."))
    monkeypatch.setattr(ai_detector_module, "ensure_dir", lambda _path: None)

    _FakeYOLO.init_count = 0
    detector = AIDetector(model_name="yolov8n.pt", conf_threshold=0.5)

    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    out1 = detector.detect(frame)
    out2 = detector.detect(frame)

    assert _FakeYOLO.init_count == 1
    assert out1.shape == frame.shape
    assert out2.shape == frame.shape
    assert np.array_equal(out1, frame + 7)
