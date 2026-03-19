"""State tracking with debounce and duration accumulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import BehaviorState
from src.core.models import BehaviorStateSnapshot, FrameFeatures


@dataclass(slots=True)
class StateTrackerConfig:
    """Thresholds for candidate-state debounce and runtime guards."""

    to_away_sec: float = 2.0
    away_to_present_sec: float = 1.5
    present_to_studying_sec: float = 3.0
    studying_to_present_sec: float = 2.0
    startup_unknown_sec: float = 0.0
    max_timestamp_gap_sec: float = 5.0
    studying_stability_threshold: float = 0.7
    studying_motion_threshold: float = 20.0


@dataclass(slots=True)
class TrackerRuntimeState:
    """Mutable runtime state for the tracker."""

    stable_state: BehaviorState = BehaviorState.UNKNOWN
    candidate_state: BehaviorState = BehaviorState.UNKNOWN
    stable_since_ts: float | None = None
    candidate_since_ts: float | None = None
    last_ts: float | None = None
    startup_since_ts: float | None = None

    # current_session_duration_sec means "continuous in-seat duration" and
    # covers both PRESENT and STUDYING until the user stably becomes AWAY.
    session_start_ts: float | None = None

    # current_away_duration_sec means the duration of the current confirmed
    # away interval, not the duration of the candidate away state.
    away_start_ts: float | None = None

    # total_present_duration_sec includes studying time by design, because
    # studying is a stricter subset of present/in-seat time.
    total_present_duration_sec: float = 0.0
    total_away_duration_sec: float = 0.0
    total_studying_duration_sec: float = 0.0
    away_count: int = 0


@dataclass(slots=True)
class BehaviorStateTracker:
    """Track stable behavior state from frame-level features."""

    config: StateTrackerConfig = field(default_factory=StateTrackerConfig)
    runtime: TrackerRuntimeState = field(default_factory=TrackerRuntimeState)

    def reset(self) -> None:
        """Reset all runtime state."""
        self.runtime = TrackerRuntimeState()

    def update(self, features: FrameFeatures) -> BehaviorStateSnapshot:
        """Update tracker with one frame of extracted features."""
        timestamp = features.timestamp
        previous_stable_state = self.runtime.stable_state

        if self.runtime.startup_since_ts is None:
            self.runtime.startup_since_ts = timestamp

        self._accumulate_duration(timestamp)

        candidate_state = self._infer_candidate_state(features)
        if candidate_state != self.runtime.candidate_state:
            self.runtime.candidate_state = candidate_state
            self.runtime.candidate_since_ts = timestamp
        elif self.runtime.candidate_since_ts is None:
            self.runtime.candidate_since_ts = timestamp

        is_state_changed = self._maybe_commit_transition(timestamp)
        return self._build_snapshot(
            frame_id=features.frame_id,
            timestamp=timestamp,
            previous_stable_state=previous_stable_state,
            is_state_changed=is_state_changed,
        )

    def _infer_candidate_state(self, features: FrameFeatures) -> BehaviorState:
        """Infer a simple, explainable candidate state from one frame."""
        timestamp = features.timestamp

        if self._is_startup_unknown(timestamp):
            return BehaviorState.UNKNOWN

        if not self._has_valid_features(features):
            return BehaviorState.UNKNOWN

        if not features.person_detected or not features.person_in_roi:
            return BehaviorState.AWAY

        if self._is_studying_candidate(features):
            return BehaviorState.STUDYING

        return BehaviorState.PRESENT

    def _is_startup_unknown(self, timestamp: float) -> bool:
        if self.config.startup_unknown_sec <= 0.0:
            return False
        if self.runtime.startup_since_ts is None:
            return True
        return (timestamp - self.runtime.startup_since_ts) < self.config.startup_unknown_sec

    @staticmethod
    def _has_valid_features(features: FrameFeatures) -> bool:
        if features.timestamp < 0:
            return False
        if features.person_detected and features.primary_bbox is None:
            return False
        if not 0.0 <= features.roi_overlap_ratio <= 1.0:
            return False
        if features.stability_score < 0.0 or features.stability_score > 1.0:
            return False
        return True

    def _is_studying_candidate(self, features: FrameFeatures) -> bool:
        """Return whether this frame qualifies as a conservative studying candidate."""
        return (
            features.person_detected
            and features.person_in_roi
            and features.primary_bbox is not None
            and features.stability_score >= self.config.studying_stability_threshold
            and features.motion_delta <= self.config.studying_motion_threshold
        )

    def _get_transition_threshold_sec(
        self,
        from_state: BehaviorState,
        to_state: BehaviorState,
    ) -> float:
        """Return debounce threshold for a stable-state transition."""
        if from_state == to_state:
            return 0.0

        if to_state == BehaviorState.AWAY:
            return self.config.to_away_sec

        if from_state == BehaviorState.AWAY and to_state in {BehaviorState.PRESENT, BehaviorState.STUDYING}:
            return self.config.away_to_present_sec

        if from_state == BehaviorState.PRESENT and to_state == BehaviorState.STUDYING:
            return self.config.present_to_studying_sec

        if from_state == BehaviorState.STUDYING and to_state == BehaviorState.PRESENT:
            return self.config.studying_to_present_sec

        if from_state == BehaviorState.UNKNOWN:
            if to_state == BehaviorState.AWAY:
                return self.config.to_away_sec
            if to_state == BehaviorState.STUDYING:
                return self.config.present_to_studying_sec
            return self.config.away_to_present_sec

        return self.config.away_to_present_sec

    def _maybe_commit_transition(self, timestamp: float) -> bool:
        """Commit candidate state to stable state after debounce."""
        if self.runtime.candidate_state == self.runtime.stable_state:
            return False

        if self.runtime.candidate_since_ts is None:
            return False

        threshold_sec = self._get_transition_threshold_sec(
            self.runtime.stable_state,
            self.runtime.candidate_state,
        )
        candidate_duration = max(0.0, timestamp - self.runtime.candidate_since_ts)
        if candidate_duration < threshold_sec:
            return False

        new_state = self.runtime.candidate_state
        self.runtime.stable_state = new_state
        self.runtime.stable_since_ts = timestamp

        if new_state == BehaviorState.AWAY:
            self.runtime.away_count += 1
            self.runtime.away_start_ts = timestamp
            self.runtime.session_start_ts = None
        elif new_state in {BehaviorState.PRESENT, BehaviorState.STUDYING}:
            if self.runtime.session_start_ts is None:
                self.runtime.session_start_ts = timestamp
            self.runtime.away_start_ts = None

        return True

    def _accumulate_duration(self, timestamp: float) -> None:
        """Accumulate duration using stable state only and guard bad timestamps."""
        if self.runtime.last_ts is None:
            self.runtime.last_ts = timestamp
            if self.runtime.stable_since_ts is None:
                self.runtime.stable_since_ts = timestamp
            return

        dt = timestamp - self.runtime.last_ts

        # Negative or repeated timestamps are ignored and do not overwrite last_ts.
        if dt <= 0:
            return

        # Large gaps are treated as discontinuities: do not accumulate them, but
        # resync last_ts so the tracker can continue on the next valid frame.
        if dt > self.config.max_timestamp_gap_sec:
            self.runtime.last_ts = timestamp
            return

        self.runtime.last_ts = timestamp

        if self.runtime.stable_state in {BehaviorState.PRESENT, BehaviorState.STUDYING}:
            self.runtime.total_present_duration_sec += dt
        elif self.runtime.stable_state == BehaviorState.AWAY:
            self.runtime.total_away_duration_sec += dt

        if self.runtime.stable_state == BehaviorState.STUDYING:
            self.runtime.total_studying_duration_sec += dt

    def _build_snapshot(
        self,
        *,
        frame_id: int,
        timestamp: float,
        previous_stable_state: BehaviorState,
        is_state_changed: bool,
    ) -> BehaviorStateSnapshot:
        """Build the public stable-state snapshot."""
        state_duration_sec = 0.0
        if self.runtime.stable_since_ts is not None and timestamp >= self.runtime.stable_since_ts:
            state_duration_sec = timestamp - self.runtime.stable_since_ts

        candidate_duration_sec = 0.0
        if self.runtime.candidate_since_ts is not None and timestamp >= self.runtime.candidate_since_ts:
            candidate_duration_sec = timestamp - self.runtime.candidate_since_ts

        current_session_duration_sec = 0.0
        if (
            self.runtime.stable_state in {BehaviorState.PRESENT, BehaviorState.STUDYING}
            and self.runtime.session_start_ts is not None
            and timestamp >= self.runtime.session_start_ts
        ):
            current_session_duration_sec = timestamp - self.runtime.session_start_ts

        current_away_duration_sec = 0.0
        if (
            self.runtime.stable_state == BehaviorState.AWAY
            and self.runtime.away_start_ts is not None
            and timestamp >= self.runtime.away_start_ts
        ):
            current_away_duration_sec = timestamp - self.runtime.away_start_ts

        return BehaviorStateSnapshot(
            frame_id=frame_id,
            timestamp=timestamp,
            current_state=self.runtime.stable_state,
            previous_state=previous_stable_state if is_state_changed else None,
            candidate_state=self.runtime.candidate_state,
            candidate_duration_sec=candidate_duration_sec,
            state_duration_sec=state_duration_sec,
            current_session_duration_sec=current_session_duration_sec,
            current_away_duration_sec=current_away_duration_sec,
            total_present_duration_sec=self.runtime.total_present_duration_sec,
            total_away_duration_sec=self.runtime.total_away_duration_sec,
            total_studying_duration_sec=self.runtime.total_studying_duration_sec,
            away_count=self.runtime.away_count,
            is_state_changed=is_state_changed,
        )


# Backward-compatible name used by the current pipeline.
StateTracker = BehaviorStateTracker
