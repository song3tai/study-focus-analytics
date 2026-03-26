"""Formal pipeline implementations for Study Focus Analytics."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from time import perf_counter, sleep
from uuid import uuid4

import cv2
import numpy as np

from src.behavior.analytics_aggregator import AnalyticsAggregator
from src.behavior.event_builder import EventBuilder
from src.behavior.focus_estimator import FocusEstimator
from src.behavior.scene_features import SceneFeatureExtractor
from src.behavior.state_tracker import BehaviorStateTracker
from src.config import AppConfig
from src.core.enums import AnalysisMode, SourceType
from src.core.models import (
    AnalysisSummary,
    BehaviorEvent,
    DetectionResult,
    FrameFeatures,
    FramePacket,
    ProcessResult,
    ROI,
    SessionResult,
)
from src.inference.ai_detector import AIDetector
from src.io.video_reader import FrameSource
from src.io.video_writer import VideoWriter
from src.utils import FPSCounter, annotate_fps


@dataclass(slots=True)
class PipelineConfig:
    """Small controls for direct frame-by-frame analysis."""

    enable_debug_logging: bool = False
    continue_on_error: bool = True
    keep_latest_result: bool = True


@dataclass(slots=True)
class LocalAnalysisPipeline:
    """Formal frame-by-frame analysis pipeline built on the V1 data flow."""

    roi: ROI
    config: PipelineConfig = field(default_factory=PipelineConfig)
    scene_feature_extractor: SceneFeatureExtractor = field(default_factory=SceneFeatureExtractor)
    state_tracker: BehaviorStateTracker = field(default_factory=BehaviorStateTracker)
    focus_estimator: FocusEstimator = field(default_factory=FocusEstimator)
    event_builder: EventBuilder = field(default_factory=EventBuilder)
    analytics_aggregator: AnalyticsAggregator = field(default_factory=AnalyticsAggregator)
    analysis_mode: AnalysisMode = AnalysisMode.REALTIME
    session_id: str = field(default_factory=lambda: str(uuid4()))
    _latest_result: ProcessResult | None = field(default=None, init=False, repr=False)
    _previous_features: FrameFeatures | None = field(default=None, init=False, repr=False)
    _events: list[BehaviorEvent] = field(default_factory=list, init=False, repr=False)

    def process_frame(
        self,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
    ) -> ProcessResult:
        """Process one detector result through the structured analysis chain."""
        try:
            frame_features = self.scene_feature_extractor.extract(
                frame_packet=frame_packet,
                detection_result=detection_result,
                roi=self.roi,
                prev_features=self._previous_features,
            )
            self._previous_features = frame_features
            state_snapshot = self.state_tracker.update(frame_features)
            focus_estimate = self.focus_estimator.estimate(frame_features, state_snapshot)
            event = self.event_builder.build(state_snapshot)
            summary = self.analytics_aggregator.update(state_snapshot, focus_estimate, event)
            result = ProcessResult(
                frame_packet=frame_packet,
                detection_result=detection_result,
                frame_features=frame_features,
                state_snapshot=state_snapshot,
                focus_estimate=focus_estimate,
                events=[event] if event is not None else [],
                summary=summary,
            )
        except Exception as exc:
            if not self.config.continue_on_error:
                raise
            result = ProcessResult(
                frame_packet=frame_packet,
                detection_result=detection_result,
                error_message=f"{type(exc).__name__}: {exc}",
            )

        if self.config.keep_latest_result:
            self._latest_result = result
        if result.events:
            self._events.extend(result.events)

        self._log_debug(result)
        return result

    def reset(self) -> None:
        """Reset runtime state for a new local analysis session."""
        self.state_tracker.reset()
        self.focus_estimator.reset()
        self.analytics_aggregator = AnalyticsAggregator()
        self.session_id = str(uuid4())
        self._latest_result = None
        self._previous_features = None
        self._events = []

    def get_latest_result(self) -> ProcessResult | None:
        return self._latest_result

    def build_session_result(self) -> SessionResult:
        latest_result = self._latest_result
        if latest_result is None:
            return SessionResult.empty(
                session_id=self.session_id,
                source_type=SourceType.FILE,
                source_name="unknown",
                analysis_mode=self.analysis_mode,
            )

        summary = latest_result.summary or AnalysisSummary()
        return SessionResult(
            session_id=self.session_id,
            source_type=latest_result.frame_packet.source_type,
            source_name=latest_result.frame_packet.source_name,
            analysis_mode=self.analysis_mode,
            summary=summary,
            events=list(self._events),
            timeline=[],
            duration_sec=summary.total_duration_sec,
        )

    def _log_debug(self, result: ProcessResult) -> None:
        if not self.config.enable_debug_logging:
            return

        if result.error_message is not None:
            print(
                "[local_pipeline] "
                f"frame={result.frame_id} ts={result.timestamp:.3f} "
                f"error={result.error_message}"
            )
            return

        snapshot = result.state_snapshot
        focus_estimate = result.focus_estimate
        if snapshot is None or focus_estimate is None:
            print(
                "[local_pipeline] "
                f"frame={result.frame_id} ts={result.timestamp:.3f} "
                "incomplete_result"
            )
            return

        print(
            "[local_pipeline] "
            f"frame={result.frame_id} "
            f"ts={result.timestamp:.3f} "
            f"candidate={snapshot.candidate_state.value if snapshot.candidate_state else 'none'} "
            f"state={snapshot.current_state.value} "
            f"focus={focus_estimate.focus_score:.3f} "
            f"focus_level={focus_estimate.focus_level.value} "
            f"candidate_dur={snapshot.candidate_duration_sec:.2f}s "
            f"state_dur={snapshot.state_duration_sec:.2f}s "
            f"away_count={snapshot.away_count}"
        )


@dataclass
class AnalysisPipeline:
    """Coordinate frame input, analysis, preview rendering, and output writing.

    Note:
        `mode` here means pipeline behavior selection (`detect` vs `analyze`).
        It is different from `AnalysisMode`, which describes execution cadence
        (`realtime` vs `fast`) for session-level workflows.
    """

    reader: FrameSource
    config: AppConfig
    mode: str
    display_enabled: bool
    writer: VideoWriter | None = None
    detector: AIDetector | None = None

    def __post_init__(self) -> None:
        self.fps_counter = FPSCounter()
        width, height = self.reader.frame_size()
        self.roi = self.config.build_roi(width=width, height=height)
        self.local_pipeline = LocalAnalysisPipeline(roi=self.roi)
        self.latest_result: ProcessResult | None = None
        self._latest_events: list[dict[str, str | float | int]] = []
        self._source_type = self._resolve_source_type()

    def run(self) -> int:
        display_enabled = self.display_enabled
        if display_enabled and not os.environ.get("DISPLAY"):
            print("[WARN] DISPLAY is not available. Running without preview window.")
            display_enabled = False

        try:
            frame_index = 0
            source_fps = self.reader.fps()
            started_monotonic = perf_counter()
            while True:
                ok, frame = self.reader.read_frame()
                if not ok:
                    if self._attempt_live_reconnect():
                        continue
                    break

                timestamp_seconds = calculate_timestamp_seconds(
                    frame_index=frame_index,
                    source_fps=source_fps,
                    is_live=self.reader.is_live,
                    started_monotonic=started_monotonic,
                )
                output_frame = self._handle_frame(frame=frame, frame_index=frame_index, timestamp_seconds=timestamp_seconds)
                annotate_fps(output_frame, self.fps_counter.tick())

                if display_enabled:
                    cv2.imshow(self.config.window_name, output_frame)

                if self.writer is not None:
                    self.writer.write_frame(output_frame)

                if display_enabled and cv2.waitKey(1) & 0xFF == 27:
                    break
                frame_index += 1
            return 0
        finally:
            self.reader.release()
            if self.writer is not None:
                self.writer.release()
            cv2.destroyAllWindows()

    def process_frame(self, frame: np.ndarray, frame_index: int, timestamp_seconds: float) -> ProcessResult:
        """Run one frame through the structured V1 analysis chain."""
        if self.detector is None:
            raise RuntimeError("AIDetector is required when mode is 'analyze'.")

        frame_packet = FramePacket(
            frame_id=frame_index,
            timestamp=timestamp_seconds,
            source_type=self._source_type,
            source_name=getattr(self.reader, "source_label", self._source_type.value),
            is_live=self.reader.is_live,
            frame=frame,
            fps_hint=self.reader.fps(),
        )
        detection_result = self.detector.detect_frame(
            frame_packet.frame,
            frame_index=frame_packet.frame_id,
            timestamp_seconds=frame_packet.timestamp,
        )
        result = self.local_pipeline.process_frame(
            frame_packet=frame_packet,
            detection_result=detection_result,
        )
        self.latest_result = result
        event = result.event
        if event is not None:
            self._latest_events.append(
                {
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp,
                    "frame_id": event.frame_id,
                    "message": event.message,
                }
            )
            self._latest_events = self._latest_events[-self.config.max_recent_events :]
        return result

    def latest_events(self) -> list[dict[str, str | float | int]]:
        return list(self._latest_events)

    def _attempt_live_reconnect(self) -> bool:
        if not self.reader.is_live:
            return False

        for attempt in range(1, self.config.live_reconnect_attempts + 1):
            print(
                f"[WARN] Live stream frame read failed. Reconnecting "
                f"({attempt}/{self.config.live_reconnect_attempts})..."
            )
            if self.reader.reconnect():
                print("[INFO] Live stream reconnected.")
                return True
            if attempt < self.config.live_reconnect_attempts:
                sleep(self.config.live_reconnect_interval_sec)

        print("[ERROR] Live stream reconnect failed.")
        return False

    def _handle_frame(self, frame: np.ndarray, frame_index: int, timestamp_seconds: float) -> np.ndarray:
        if self.mode == "analyze":
            result = self.process_frame(frame=frame, frame_index=frame_index, timestamp_seconds=timestamp_seconds)
            return self._render_analysis_overlay(result)

        if self.mode == "detect":
            if self.detector is None:
                raise RuntimeError("AIDetector is required when mode is 'detect'.")
            detection_result = self.detector.detect_frame(
                frame,
                frame_index=frame_index,
                timestamp_seconds=timestamp_seconds,
            )
            return self.detector.annotate(frame=frame, detection_result=detection_result)

        raise ValueError(f"Unsupported pipeline mode: {self.mode}")

    def _render_analysis_overlay(self, result: ProcessResult) -> np.ndarray:
        return render_analysis_preview(
            result=result,
            roi=self.roi,
            detector=self.detector,
        )

    @staticmethod
    def _draw_roi(frame: np.ndarray, roi: ROI) -> None:
        cv2.rectangle(frame, (roi.x1, roi.y1), (roi.x2, roi.y2), (255, 200, 0), 2)

    def _resolve_source_type(self) -> SourceType:
        if getattr(self.reader, "stream_url", None):
            return SourceType.RTSP
        if getattr(self.reader, "camera_index", None) is not None:
            return SourceType.CAMERA
        return SourceType.FILE


def render_analysis_preview(
    *,
    result: ProcessResult,
    roi: ROI,
    detector: AIDetector | None,
    draw_roi: bool = True,
) -> np.ndarray:
    """Render a lightweight preview frame for CLI and web MJPEG consumers."""
    base_frame = result.frame_packet.frame.copy()
    frame = detector.annotate(base_frame, result.detection_result) if detector else base_frame
    if draw_roi:
        AnalysisPipeline._draw_roi(frame, roi)

    if (
        result.error_message is not None
        or result.state_snapshot is None
        or result.focus_estimate is None
        or result.summary is None
    ):
        cv2.putText(
            frame,
            result.error_message or "analysis result unavailable",
            (12, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
        return frame

    lines = [
        f"State: {result.state_snapshot.current_state.value}",
        f"Focus: {result.focus_estimate.focus_score:.1f} ({result.focus_estimate.focus_level.value})",
        f"Present: {result.summary.total_present_duration_sec:.1f}s",
        f"Away: {result.summary.total_away_duration_sec:.1f}s",
        f"Studying: {result.summary.total_studying_duration_sec:.1f}s",
    ]
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (12, 58 + (index * 26)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return frame


def calculate_timestamp_seconds(
    *,
    frame_index: int,
    source_fps: float,
    is_live: bool,
    started_monotonic: float,
    now_monotonic: float | None = None,
) -> float:
    """Return frame timestamp in seconds for file and live sources.

    File sources follow the media timeline. Live sources follow elapsed wall-clock
    time so downstream duration counters match real time even when processing FPS
    drops below the camera/stream's advertised FPS.
    """
    if is_live:
        current_monotonic = perf_counter() if now_monotonic is None else now_monotonic
        return max(0.0, current_monotonic - started_monotonic)

    return frame_index / max(source_fps, 1e-6)







