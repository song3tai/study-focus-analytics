"""Lightweight local analysis pipeline for frame-by-frame orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.behavior.focus_estimator import FocusEstimator
from src.behavior.scene_features import SceneFeatureExtractor
from src.behavior.state_tracker import BehaviorStateTracker
from src.core.models import (
    BehaviorStateSnapshot,
    DetectionResult,
    FocusEstimate,
    FrameFeatures,
    FramePacket,
    ProcessResult,
    ROI,
)


@dataclass(slots=True)
class PipelineConfig:
    """Small set of controls for local frame analysis orchestration."""

    enable_debug_logging: bool = False
    continue_on_error: bool = True
    keep_latest_result: bool = True


@dataclass(slots=True)
class LocalAnalysisPipeline:
    """Chain scene features, state tracking, and focus estimation for one local analysis session."""

    roi: ROI
    config: PipelineConfig = field(default_factory=PipelineConfig)
    scene_feature_extractor: SceneFeatureExtractor = field(default_factory=SceneFeatureExtractor)
    state_tracker: BehaviorStateTracker = field(default_factory=BehaviorStateTracker)
    focus_estimator: FocusEstimator = field(default_factory=FocusEstimator)
    _latest_result: ProcessResult | None = field(default=None, init=False, repr=False)
    _previous_features: FrameFeatures | None = field(default=None, init=False, repr=False)

    def process_frame(
        self,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
    ) -> ProcessResult:
        """Process one frame packet and its detector output."""
        try:
            frame_features = self._extract_features(frame_packet, detection_result)
            state_snapshot = self._track_state(frame_features)
            focus_estimate = self._estimate_focus(frame_features, state_snapshot)
            result = self._build_result(
                frame_packet=frame_packet,
                detection_result=detection_result,
                frame_features=frame_features,
                state_snapshot=state_snapshot,
                focus_estimate=focus_estimate,
            )
        except Exception as exc:
            if not self.config.continue_on_error:
                raise
            result = self._build_error_result(
                frame_packet=frame_packet,
                detection_result=detection_result,
                exc=exc,
            )

        if self.config.keep_latest_result:
            self._latest_result = result

        self._log_debug(result)
        return result

    def reset(self) -> None:
        """Reset tracker state and cached results; FocusEstimator is stateless and needs no reset."""
        self.state_tracker.reset()
        self._latest_result = None
        self._previous_features = None

    def get_latest_result(self) -> ProcessResult | None:
        """Return the latest successfully processed or error result."""
        return self._latest_result

    def _extract_features(
        self,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
    ) -> FrameFeatures:
        frame_features = self.scene_feature_extractor.extract(
            frame_packet=frame_packet,
            detection_result=detection_result,
            roi=self.roi,
            prev_features=self._previous_features,
        )
        self._previous_features = frame_features
        return frame_features

    def _track_state(self, frame_features: FrameFeatures) -> BehaviorStateSnapshot:
        return self.state_tracker.update(frame_features)

    def _estimate_focus(
        self,
        frame_features: FrameFeatures,
        state_snapshot: BehaviorStateSnapshot,
    ) -> FocusEstimate:
        return self.focus_estimator.estimate(frame_features, state_snapshot)

    @staticmethod
    def _build_result(
        *,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
        frame_features: FrameFeatures,
        state_snapshot: BehaviorStateSnapshot,
        focus_estimate: FocusEstimate,
    ) -> ProcessResult:
        return ProcessResult(
            frame_packet=frame_packet,
            detection_result=detection_result,
            frame_features=frame_features,
            state_snapshot=state_snapshot,
            focus_estimate=focus_estimate,
        )

    @staticmethod
    def _build_error_result(
        *,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
        exc: Exception,
    ) -> ProcessResult:
        return ProcessResult(
            frame_packet=frame_packet,
            detection_result=detection_result,
            error_message=f"{type(exc).__name__}: {exc}",
        )

    def _log_debug(self, result: ProcessResult) -> None:
        if not self.config.enable_debug_logging:
            return

        if result.error_message is not None:
            print(
                "[pipeline] "
                f"frame={result.frame_id} ts={result.timestamp:.3f} "
                f"error={result.error_message}"
            )
            return

        snapshot = result.state_snapshot
        if snapshot is None:
            print(
                "[pipeline] "
                f"frame={result.frame_id} ts={result.timestamp:.3f} "
                "state_snapshot=None"
            )
            return

        print(
            "[pipeline] "
            f"frame={result.frame_id} "
            f"ts={result.timestamp:.3f} "
            f"candidate={snapshot.candidate_state.value if snapshot.candidate_state else 'none'} "
            f"state={snapshot.current_state.value} "
            f"focus={result.focus_estimate.focus_score:.3f} "
            f"focus_level={result.focus_estimate.focus_level.value} "
            f"candidate_dur={snapshot.candidate_duration_sec:.2f}s "
            f"state_dur={snapshot.state_duration_sec:.2f}s "
            f"away_count={snapshot.away_count}"
        )
