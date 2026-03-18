"""Aggregate frame-level behavior outputs into session summaries."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.enums import BehaviorState, EventType
from src.core.models import AnalysisSummary, BehaviorEvent, BehaviorStateSnapshot, FocusEstimate


@dataclass
class AnalyticsAggregator:
    """Maintain running summary statistics for one analysis session."""

    _last_timestamp_seconds: float | None = None
    _summary: AnalysisSummary = AnalysisSummary()
    _focus_total: float = 0.0
    _focus_count: int = 0

    def update(
        self,
        snapshot: BehaviorStateSnapshot,
        focus_estimate: FocusEstimate,
        event: BehaviorEvent | None,
    ) -> AnalysisSummary:
        delta = 0.0
        if self._last_timestamp_seconds is not None:
            delta = max(0.0, snapshot.timestamp_seconds - self._last_timestamp_seconds)
        self._last_timestamp_seconds = snapshot.timestamp_seconds

        summary = self._summary
        total_duration = summary.total_duration_seconds + delta
        present_duration = summary.present_duration_seconds
        away_duration = summary.away_duration_seconds
        studying_duration = summary.studying_duration_seconds
        unknown_duration = summary.unknown_duration_seconds

        if snapshot.state == BehaviorState.PRESENT:
            present_duration += delta
        elif snapshot.state == BehaviorState.AWAY:
            away_duration += delta
        elif snapshot.state == BehaviorState.STUDYING:
            present_duration += delta
            studying_duration += delta
        else:
            unknown_duration += delta

        away_count = summary.away_count
        event_count = summary.event_count
        if event is not None:
            event_count += 1
            if event.event_type == EventType.AWAY_STARTED:
                away_count += 1

        self._focus_total += focus_estimate.focus_score
        self._focus_count += 1
        average_focus = self._focus_total / self._focus_count
        max_focus = focus_estimate.focus_score if self._focus_count == 1 else max(summary.max_focus_score, focus_estimate.focus_score)
        min_focus = focus_estimate.focus_score if self._focus_count == 1 else min(summary.min_focus_score, focus_estimate.focus_score)

        self._summary = AnalysisSummary(
            total_duration_seconds=round(total_duration, 3),
            present_duration_seconds=round(present_duration, 3),
            away_duration_seconds=round(away_duration, 3),
            studying_duration_seconds=round(studying_duration, 3),
            unknown_duration_seconds=round(unknown_duration, 3),
            away_count=away_count,
            event_count=event_count,
            average_focus_score=round(average_focus, 2),
            max_focus_score=round(max_focus, 2),
            min_focus_score=round(min_focus, 2),
            current_state=snapshot.state,
        )
        return self._summary
