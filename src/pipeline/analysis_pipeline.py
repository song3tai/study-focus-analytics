"""Structured analysis pipeline for Study Focus Analytics."""

from __future__ import annotations

import os
from dataclasses import dataclass
from time import sleep

import cv2
import numpy as np

from src.behavior.analytics_aggregator import AnalyticsAggregator
from src.behavior.event_builder import EventBuilder
from src.behavior.focus_estimator import FocusEstimator
from src.behavior.scene_features import SceneFeatureExtractor
from src.behavior.state_tracker import StateTracker
from src.config import AppConfig
from src.core.enums import SourceType
from src.core.models import FramePacket, ProcessResult, ROI
from src.inference.ai_detector import AIDetector
from src.io.video_reader import FrameSource
from src.io.video_writer import VideoWriter
from src.utils import FPSCounter, annotate_fps


@dataclass
class AnalysisPipeline:
    """Coordinate frame input, analysis, preview rendering, and output writing."""

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
        self.scene_feature_extractor = SceneFeatureExtractor()
        self.state_tracker = StateTracker()
        self.focus_estimator = FocusEstimator()
        self.event_builder = EventBuilder()
        self.analytics_aggregator = AnalyticsAggregator()
        self.latest_result: ProcessResult | None = None
        self._latest_events: list[dict[str, str | float | int]] = []
        self._source_type = self._resolve_source_type()
        self._previous_features = None

    def run(self) -> int:
        display_enabled = self.display_enabled
        if display_enabled and not os.environ.get("DISPLAY"):
            print("[WARN] DISPLAY is not available. Running without preview window.")
            display_enabled = False

        try:
            frame_index = 0
            source_fps = self.reader.fps()
            while True:
                ok, frame = self.reader.read_frame()
                if not ok:
                    if self._attempt_live_reconnect():
                        continue
                    break

                timestamp_seconds = frame_index / max(source_fps, 1e-6)
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
        self.latest_result = result
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
        frame = self.detector.annotate(result.frame_packet.frame, result.detection_result) if self.detector else result.frame_packet.frame.copy()
        self._draw_roi(frame, self.roi)

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

    @staticmethod
    def _draw_roi(frame: np.ndarray, roi: ROI) -> None:
        cv2.rectangle(frame, (roi.x1, roi.y1), (roi.x2, roi.y2), (255, 200, 0), 2)

    def _resolve_source_type(self) -> SourceType:
        if getattr(self.reader, "stream_url", None):
            return SourceType.RTSP
        if getattr(self.reader, "camera_index", None) is not None:
            return SourceType.CAMERA
        return SourceType.FILE
