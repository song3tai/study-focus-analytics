"""Debounced state machine for present/away/studying classification."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.enums import BehaviorState
from src.core.models import BehaviorStateSnapshot, FrameFeatures


@dataclass
class StateTracker:
    """Maintain the behavior state machine across frames."""

    present_confirm_seconds: float = 1.0
    away_confirm_seconds: float = 2.0
    studying_confirm_seconds: float = 10.0
    studying_min_stability: float = 0.6
    current_state: BehaviorState = BehaviorState.UNKNOWN
    _state_since_seconds: float = 0.0
    _candidate_state: BehaviorState | None = None
    _candidate_since_seconds: float | None = None
    _presence_since_seconds: float | None = None

    def update(self, features: FrameFeatures) -> BehaviorStateSnapshot:
        observed_state = self._observe_state(features)
        transition_from = self.current_state

        if observed_state != self.current_state:
            confirm_seconds = self._confirm_seconds(observed_state)
            if confirm_seconds <= 0.0:
                self.current_state = observed_state
                self._state_since_seconds = features.timestamp_seconds
                self._candidate_state = None
                self._candidate_since_seconds = None
            elif self._candidate_state != observed_state:
                self._candidate_state = observed_state
                self._candidate_since_seconds = features.timestamp_seconds
            else:
                started_at = (
                    self._candidate_since_seconds
                    if self._candidate_since_seconds is not None
                    else features.timestamp_seconds
                )
                if features.timestamp_seconds - started_at >= confirm_seconds:
                    self.current_state = observed_state
                    self._state_since_seconds = features.timestamp_seconds
                    self._candidate_state = None
                    self._candidate_since_seconds = None
        else:
            self._candidate_state = None
            self._candidate_since_seconds = None

        previous_state = transition_from if transition_from != self.current_state else None
        return BehaviorStateSnapshot(
            frame_index=features.frame_index,
            timestamp_seconds=features.timestamp_seconds,
            state=self.current_state,
            previous_state=previous_state,
            state_since_seconds=self._state_since_seconds,
            state_duration_seconds=max(0.0, features.timestamp_seconds - self._state_since_seconds),
            continuous_presence_seconds=self._continuous_presence_seconds(features.timestamp_seconds),
            person_in_roi=features.person_in_roi,
            stability_score=features.stability_score,
        )

    def _observe_state(self, features: FrameFeatures) -> BehaviorState:
        if features.person_in_roi:
            if self._presence_since_seconds is None:
                self._presence_since_seconds = features.timestamp_seconds
        else:
            self._presence_since_seconds = None

        if not features.person_in_roi:
            return BehaviorState.AWAY

        presence_duration = self._continuous_presence_seconds(features.timestamp_seconds)
        if (
            presence_duration >= self.studying_confirm_seconds
            and features.stability_score >= self.studying_min_stability
        ):
            return BehaviorState.STUDYING
        return BehaviorState.PRESENT

    def _continuous_presence_seconds(self, now_seconds: float) -> float:
        if self._presence_since_seconds is None:
            return 0.0
        return max(0.0, now_seconds - self._presence_since_seconds)

    def _confirm_seconds(self, state: BehaviorState) -> float:
        if state == BehaviorState.AWAY:
            return self.away_confirm_seconds
        if state == BehaviorState.PRESENT:
            return self.present_confirm_seconds
        if state == BehaviorState.STUDYING:
            return 0.0
        return 0.0
