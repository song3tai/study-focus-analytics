"""Lightweight and explainable focus estimation."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import BehaviorState, FocusLevel
from src.core.models import BehaviorStateSnapshot, FocusEstimate, FrameFeatures


@dataclass(slots=True)
class FocusEstimatorConfig:
    """Config for explainable focus scoring."""

    away_base_score: float = 0.0
    unknown_base_score: float = 0.15
    present_base_score: float = 0.45
    studying_base_score: float = 0.75

    state_weight: float = 0.40
    stability_weight: float = 0.25
    roi_weight: float = 0.20
    motion_weight: float = 0.15

    motion_good_threshold: float = 0.10
    motion_bad_threshold: float = 0.50

    low_level_threshold: float = 0.40
    high_level_threshold: float = 0.70

    away_score_cap: float = 0.15
    unknown_score_cap: float = 0.35


@dataclass(slots=True)
class FocusEstimator:
    """Estimate focus from stable state output and current frame features."""

    config: FocusEstimatorConfig = field(default_factory=FocusEstimatorConfig)

    def estimate(
        self,
        features: FrameFeatures,
        state_snapshot: BehaviorStateSnapshot,
    ) -> FocusEstimate:
        """Estimate focus for one frame from features and stable state."""

        state_subscore = self._compute_state_subscore(state_snapshot)
        stability_subscore = self._compute_stability_subscore(features)
        roi_subscore = self._compute_roi_subscore(features)
        motion_subscore = self._compute_motion_subscore(features)

        subscores = {
            "state": state_subscore,
            "stability": stability_subscore,
            "roi": roi_subscore,
            "motion": motion_subscore,
        }
        score = self._combine_subscores(subscores, state_snapshot.current_state)
        score = self._clamp(score)

        return FocusEstimate(
            frame_id=state_snapshot.frame_id,
            timestamp=state_snapshot.timestamp,
            focus_score=round(score, 4),
            focus_level=self._score_to_level(score),
            reasons=self._build_reasons(state_snapshot, features, subscores),
            subscores={name: round(value, 4) for name, value in subscores.items()},
        )

    def reset(self) -> None:
        """Reserved for future stateful variants; current implementation is stateless."""
        return None

    def _compute_state_subscore(self, state_snapshot: BehaviorStateSnapshot) -> float:
        state = state_snapshot.current_state
        if state == BehaviorState.AWAY:
            return self.config.away_base_score
        if state == BehaviorState.UNKNOWN:
            return self.config.unknown_base_score
        if state == BehaviorState.PRESENT:
            return self.config.present_base_score
        if state == BehaviorState.STUDYING:
            return self.config.studying_base_score
        return self.config.unknown_base_score

    def _compute_stability_subscore(self, features: FrameFeatures) -> float:
        return self._clamp(features.stability_score)

    def _compute_roi_subscore(self, features: FrameFeatures) -> float:
        if not features.person_detected:
            return 0.0

        overlap = self._clamp(features.roi_overlap_ratio)
        if not features.person_in_roi:
            return 0.1
        return max(0.6, overlap)

    def _compute_motion_subscore(self, features: FrameFeatures) -> float:
        motion = max(0.0, features.motion_delta)
        good = self.config.motion_good_threshold
        bad = max(good, self.config.motion_bad_threshold)

        if motion <= good:
            return 1.0
        if motion >= bad:
            return 0.0

        span = bad - good
        if span <= 0:
            return 0.0
        return 1.0 - ((motion - good) / span)

    def _combine_subscores(
        self,
        subscores: dict[str, float],
        state: BehaviorState,
    ) -> float:
        weight_sum = (
            self.config.state_weight
            + self.config.stability_weight
            + self.config.roi_weight
            + self.config.motion_weight
        )
        if weight_sum <= 0:
            return 0.0

        weighted_score = (
            (subscores["state"] * self.config.state_weight)
            + (subscores["stability"] * self.config.stability_weight)
            + (subscores["roi"] * self.config.roi_weight)
            + (subscores["motion"] * self.config.motion_weight)
        ) / weight_sum

        if state == BehaviorState.AWAY:
            return min(weighted_score, self.config.away_score_cap)
        if state == BehaviorState.UNKNOWN:
            return min(weighted_score, self.config.unknown_score_cap)
        return weighted_score

    def _score_to_level(self, score: float) -> FocusLevel:
        score = self._clamp(score)
        if score >= self.config.high_level_threshold:
            return FocusLevel.HIGH
        if score >= self.config.low_level_threshold:
            return FocusLevel.MEDIUM
        return FocusLevel.LOW

    def _build_reasons(
        self,
        state_snapshot: BehaviorStateSnapshot,
        features: FrameFeatures,
        subscores: dict[str, float],
    ) -> list[str]:
        reasons = [f"state={state_snapshot.current_state.value}"]

        if subscores["stability"] >= 0.7:
            reasons.append("high_stability")
        elif subscores["stability"] <= 0.3:
            reasons.append("low_stability")

        if features.person_in_roi and subscores["roi"] >= 0.6:
            reasons.append("in_study_roi")
        else:
            reasons.append("not_in_roi")

        if subscores["motion"] >= 0.7:
            reasons.append("low_motion")
        elif subscores["motion"] <= 0.3:
            reasons.append("high_motion")

        return reasons

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
