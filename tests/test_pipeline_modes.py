from __future__ import annotations

import numpy as np
import pytest

import src.pipeline.analysis_pipeline as pipeline_module
from src.config import AppConfig
from src.core.enums import BehaviorState, FocusLevel, SourceType
from src.core.models import BBox, Detection, DetectionResult, FramePacket, ROI
from src.pipeline import LocalAnalysisPipeline, PipelineConfig
from src.pipeline.analysis_pipeline import AnalysisPipeline, calculate_timestamp_seconds, render_analysis_preview


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
            frame_id=frame_index,
            timestamp=timestamp_seconds,
            detections=[
                Detection(
                    class_id=0,
                    class_name="person",
                    confidence=0.9,
                    bbox=BBox(x1=1, y1=1, x2=6, y2=6),
                ),
            ],
            inference_ms=3.0,
            model_name="dummy-yolo",
        )

    def annotate(self, frame: np.ndarray, detection_result: DetectionResult) -> np.ndarray:
        return frame + len(detection_result.detections)


def _frames(n: int = 3) -> list[np.ndarray]:
    return [np.zeros((8, 8, 3), dtype=np.uint8) for _ in range(n)]


def _frame_packet(frame_id: int = 1, timestamp: float = 0.1) -> FramePacket:
    return FramePacket(
        frame_id=frame_id,
        timestamp=timestamp,
        source_type=SourceType.FILE,
        source_name="sample.mp4",
        is_live=False,
        frame=np.zeros((100, 100, 3), dtype=np.uint8),
        fps_hint=10.0,
    )


def _detection_result(frame_id: int = 1, timestamp: float = 0.1) -> DetectionResult:
    return DetectionResult(
        frame_id=frame_id,
        timestamp=timestamp,
        detections=[
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.95,
                bbox=BBox(x1=30, y1=20, x2=70, y2=90),
            )
        ],
        inference_ms=2.5,
        model_name="dummy-yolo",
    )


def test_local_analysis_pipeline_returns_full_process_result() -> None:
    pipeline = LocalAnalysisPipeline(roi=ROI(x=20, y=15, w=60, h=75))

    result = pipeline.process_frame(
        frame_packet=_frame_packet(),
        detection_result=_detection_result(),
    )

    assert result.error_message is None
    assert result.frame_features is not None
    assert result.state_snapshot is not None
    assert result.focus_estimate is not None
    assert result.summary is not None
    assert result.state_snapshot.current_state in {BehaviorState.UNKNOWN, BehaviorState.PRESENT, BehaviorState.STUDYING}
    assert result.focus_estimate.focus_level in {FocusLevel.LOW, FocusLevel.MEDIUM, FocusLevel.HIGH}


def test_local_analysis_pipeline_returns_error_result_when_continue_on_error(monkeypatch) -> None:
    pipeline = LocalAnalysisPipeline(
        roi=ROI(x=20, y=15, w=60, h=75),
        config=PipelineConfig(continue_on_error=True),
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        type(pipeline.scene_feature_extractor),
        "extract",
        _boom,
    )

    result = pipeline.process_frame(
        frame_packet=_frame_packet(),
        detection_result=_detection_result(),
    )

    assert result.error_message == "RuntimeError: boom"
    assert result.frame_features is None
    assert result.state_snapshot is None
    assert result.focus_estimate is None
    assert result.summary is None


def test_video_analysis_pipeline_detect_mode_uses_detector_and_writer() -> None:
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


def test_video_analysis_pipeline_analyze_mode_produces_structured_result() -> None:
    reader = DummyReader(_frames(12))
    detector = DummyDetector()

    pipeline = AnalysisPipeline(
        reader=reader,
        config=AppConfig(),
        mode="analyze",
        display_enabled=False,
        writer=None,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert pipeline.latest_result is not None
    assert pipeline.latest_result.frame_features is not None
    assert pipeline.latest_result.state_snapshot is not None
    assert pipeline.latest_result.focus_estimate is not None
    assert pipeline.latest_result.summary is not None


def test_video_analysis_pipeline_detect_mode_requires_detector() -> None:
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


def test_video_analysis_pipeline_annotates_fps_for_each_frame(monkeypatch) -> None:
    reader = DummyReader(_frames(2))
    annotated_values: list[float] = []

    monkeypatch.setattr(pipeline_module, "annotate_fps", lambda frame, fps: annotated_values.append(fps) or frame)

    class FakeFPSCounter:
        def __init__(self) -> None:
            self._values = iter((12.5, 13.0))

        def tick(self) -> float:
            return next(self._values)

    monkeypatch.setattr(pipeline_module, "FPSCounter", FakeFPSCounter)

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


def test_render_analysis_preview_does_not_mutate_original_frame() -> None:
    frame_packet = FramePacket(
        frame_id=1,
        timestamp=0.1,
        source_type=SourceType.FILE,
        source_name="sample.mp4",
        is_live=False,
        frame=np.zeros((20, 20, 3), dtype=np.uint8),
        fps_hint=10.0,
    )
    detection_result = DetectionResult(
        frame_id=1,
        timestamp=0.1,
        detections=[],
        inference_ms=1.0,
        model_name="dummy",
    )
    result = LocalAnalysisPipeline(roi=ROI(x=2, y=2, w=10, h=10)).process_frame(
        frame_packet=frame_packet,
        detection_result=detection_result,
    )

    original = result.frame_packet.frame.copy()
    preview = render_analysis_preview(result=result, roi=ROI(x=2, y=2, w=10, h=10), detector=None)

    assert np.array_equal(result.frame_packet.frame, original)
    assert preview.shape == original.shape
    assert not np.array_equal(preview, original)


def test_render_analysis_preview_can_skip_roi_overlay() -> None:
    frame_packet = FramePacket(
        frame_id=1,
        timestamp=0.1,
        source_type=SourceType.FILE,
        source_name="sample.mp4",
        is_live=False,
        frame=np.zeros((24, 24, 3), dtype=np.uint8),
        fps_hint=10.0,
    )
    result = LocalAnalysisPipeline(roi=ROI(x=4, y=4, w=10, h=10)).process_frame(
        frame_packet=frame_packet,
        detection_result=DetectionResult(frame_id=1, timestamp=0.1, detections=[], inference_ms=1.0, model_name="dummy"),
    )

    with_roi = render_analysis_preview(result=result, roi=ROI(x=4, y=4, w=10, h=10), detector=None, draw_roi=True)
    without_roi = render_analysis_preview(result=result, roi=ROI(x=4, y=4, w=10, h=10), detector=None, draw_roi=False)

    assert not np.array_equal(with_roi, without_roi)


def test_calculate_timestamp_seconds_uses_media_timeline_for_file_sources() -> None:
    timestamp = calculate_timestamp_seconds(
        frame_index=15,
        source_fps=10.0,
        is_live=False,
        started_monotonic=100.0,
        now_monotonic=106.0,
    )

    assert timestamp == 1.5


def test_calculate_timestamp_seconds_uses_wall_clock_for_live_sources() -> None:
    timestamp = calculate_timestamp_seconds(
        frame_index=15,
        source_fps=30.0,
        is_live=True,
        started_monotonic=100.0,
        now_monotonic=106.25,
    )

    assert timestamp == 6.25
