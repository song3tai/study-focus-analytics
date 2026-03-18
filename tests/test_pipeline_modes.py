from __future__ import annotations

import numpy as np
import pytest

import src.pipeline.analysis_pipeline as pipeline_module
from src.config import AppConfig
from src.core.enums import BehaviorState, FocusLevel
from src.core.models import Detection, DetectionResult, ROI
from src.pipeline import AnalysisPipeline


class DummyReader:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = frames
        self._idx = 0
        self.released = False
        self.is_live = False
        self.source_label = "dummy"

    def read_frame(self):
        if self._idx >= len(self._frames):
            return False, None
        frame = self._frames[self._idx]
        self._idx += 1
        return True, frame

    def fps(self) -> float:
        return 10.0

    def frame_size(self) -> tuple[int, int]:
        frame = self._frames[0]
        return frame.shape[1], frame.shape[0]

    def release(self) -> None:
        self.released = True

    def reconnect(self) -> bool:
        return False


class DummyWriter:
    def __init__(self) -> None:
        self.frames_written = 0
        self.released = False

    def write_frame(self, frame: np.ndarray) -> None:
        self.frames_written += 1

    def release(self) -> None:
        self.released = True


class DummyDetector:
    def __init__(self) -> None:
        self.calls = 0

    def detect_frame(self, frame: np.ndarray, *, frame_index: int, timestamp_seconds: float) -> DetectionResult:
        self.calls += 1
        return DetectionResult(
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            detections=[
                Detection(label="person", confidence=0.9, bbox=ROI(x1=1, y1=1, x2=6, y2=6)),
            ],
        )

    def annotate(self, frame: np.ndarray, detection_result: DetectionResult) -> np.ndarray:
        return frame + len(detection_result.detections)


def _frames(n: int = 3) -> list[np.ndarray]:
    return [np.zeros((8, 8, 3), dtype=np.uint8) for _ in range(n)]


def test_pipeline_detect_mode_uses_detector_and_writer() -> None:
    reader = DummyReader(_frames(3))
    detector = DummyDetector()
    writer = DummyWriter()

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=writer,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert detector.calls == 3
    assert writer.frames_written == 3
    assert reader.released is True
    assert writer.released is True


def test_pipeline_detect_mode_uses_detector_not_processor() -> None:
    reader = DummyReader(_frames(2))
    detector = DummyDetector()

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert detector.calls == 2
    assert reader.released is True


def test_pipeline_annotates_fps_for_each_frame(monkeypatch) -> None:
    reader = DummyReader(_frames(2))
    annotated_values: list[float] = []

    monkeypatch.setattr(pipeline_module, "annotate_fps", lambda frame, fps: annotated_values.append(fps) or frame)

    class _FakeFPSCounter:
        def __init__(self) -> None:
            self._values = iter((12.5, 13.0))

        def tick(self) -> float:
            return next(self._values)

    monkeypatch.setattr(pipeline_module, "FPSCounter", _FakeFPSCounter)

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=DummyDetector(),
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert annotated_values == [12.5, 13.0]


def test_pipeline_detect_mode_requires_detector() -> None:
    reader = DummyReader(_frames(1))

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=None,
    )

    with pytest.raises(RuntimeError, match="AIDetector is required"):
        pipeline.run()

    assert reader.released is True


class DummyLiveReader(DummyReader):
    def __init__(self, frames: list[np.ndarray], reconnect_results: list[bool]) -> None:
        super().__init__(frames)
        self.is_live = True
        self._reconnect_results = reconnect_results
        self.reconnect_calls = 0
        self._first_read_failed = False

    def read_frame(self):
        if not self._first_read_failed:
            self._first_read_failed = True
            return False, None
        if self._idx >= len(self._frames):
            self.is_live = False
        return super().read_frame()

    def reconnect(self) -> bool:
        self.reconnect_calls += 1
        if not self._reconnect_results:
            return False
        return self._reconnect_results.pop(0)


def test_pipeline_reconnects_live_source_and_continues(monkeypatch) -> None:
    monkeypatch.setattr(pipeline_module, "sleep", lambda _seconds: None)

    reader = DummyLiveReader(_frames(2), reconnect_results=[True])
    detector = DummyDetector()

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(live_reconnect_attempts=2, live_reconnect_interval_sec=0.01),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert reader.reconnect_calls == 1
    assert detector.calls == 2


def test_pipeline_stops_after_live_reconnect_failures(monkeypatch) -> None:
    monkeypatch.setattr(pipeline_module, "sleep", lambda _seconds: None)

    reader = DummyLiveReader(_frames(2), reconnect_results=[False, False])

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(live_reconnect_attempts=2, live_reconnect_interval_sec=0.01),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=DummyDetector(),
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert reader.reconnect_calls == 2


def test_pipeline_analyze_mode_produces_structured_result() -> None:
    reader = DummyReader(_frames(12))
    detector = DummyDetector()

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(
            present_confirm_seconds=0.0,
            away_confirm_seconds=0.0,
            studying_confirm_seconds=0.3,
        ),
        mode="analyze",
        display_enabled=False,
        writer=None,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert pipeline.latest_result is not None
    assert pipeline.latest_result.state_snapshot.state in {BehaviorState.PRESENT, BehaviorState.STUDYING}
    assert pipeline.latest_result.focus_estimate.focus_level in {
        FocusLevel.LOW,
        FocusLevel.MEDIUM,
        FocusLevel.HIGH,
    }
    assert pipeline.latest_result.summary.present_duration_seconds > 0.0
