"""Explainable rule-based focus estimator."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from src.core.enums import BehaviorState, FocusLevel
from src.core.models import BehaviorStateSnapshot, FocusEstimate, FrameFeatures


@dataclass
class FocusEstimator:
    """Estimate focus from recent windowed state and feature history."""

    max_window_size: int = 120
    _history: deque[tuple[BehaviorStateSnapshot, FrameFeatures]] = field(default_factory=deque)

    def estimate(self, snapshot: BehaviorStateSnapshot, features: FrameFeatures) -> FocusEstimate:
        self._history.append((snapshot, features))
        while len(self._history) > self.max_window_size:
            self._history.popleft()

        snapshots = [item[0] for item in self._history]
        feature_items = [item[1] for item in self._history]

        present_ratio = self._ratio_for_states(snapshots, {BehaviorState.PRESENT, BehaviorState.STUDYING})
        studying_ratio = self._ratio_for_states(snapshots, {BehaviorState.STUDYING})
        avg_stability = sum(item.stability_score for item in feature_items) / len(feature_items)
        avg_roi_overlap = sum(item.roi_overlap_ratio for item in feature_items) / len(feature_items)
        away_entries = sum(
            1
            for item in snapshots
            if item.previous_state is not None and item.state == BehaviorState.AWAY
        )

        score = (present_ratio * 45.0) + (studying_ratio * 30.0) + (avg_stability * 15.0) + (avg_roi_overlap * 10.0)
        score -= away_entries * 8.0
        score = max(0.0, min(100.0, score))

        reasons: list[str] = []
        if studying_ratio >= 0.5:
            reasons.append("recent window is dominated by studying state")
        elif present_ratio >= 0.7:
            reasons.append("presence in ROI has stayed stable")
        else:
            reasons.append("presence in ROI is not stable enough yet")

        if away_entries > 0:
            reasons.append("recent away transitions lowered the score")
        if avg_stability >= 0.7:
            reasons.append("motion is low and ROI alignment is steady")

        return FocusEstimate(
            focus_score=round(score, 2),
            focus_level=self._level_for_score(score),
            reasons=reasons,
        )

    @staticmethod
    def _ratio_for_states(
        snapshots: list[BehaviorStateSnapshot],
        target_states: set[BehaviorState],
    ) -> float:
        if not snapshots:
            return 0.0
        matched = sum(1 for snapshot in snapshots if snapshot.state in target_states)
        return matched / len(snapshots)

    @staticmethod
    def _level_for_score(score: float) -> FocusLevel:
        if score >= 75:
            return FocusLevel.HIGH
        if score >= 40:
            return FocusLevel.MEDIUM
        return FocusLevel.LOW
