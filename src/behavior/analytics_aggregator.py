"""Aggregate frame-level behavior outputs into session summaries."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import BehaviorState, EventType
from src.core.models import AnalysisSummary, BehaviorEvent, BehaviorStateSnapshot, FocusEstimate


@dataclass
class AnalyticsAggregator:
    """Maintain running summary statistics for one analysis session."""

    _last_timestamp: float | None = None
    _summary: AnalysisSummary = field(default_factory=AnalysisSummary)
    _focus_total: float = 0.0
    _focus_count: int = 0

    def update(
        self,
        snapshot: BehaviorStateSnapshot,
        focus_estimate: FocusEstimate,
        event: BehaviorEvent | None,
    ) -> AnalysisSummary:
        delta = 0.0
        if self._last_timestamp is not None:
            delta = max(0.0, snapshot.timestamp - self._last_timestamp)
        self._last_timestamp = snapshot.timestamp

        summary = self._summary
        total_duration = summary.total_duration_sec + delta
        away_count = summary.away_count
        if event is not None and event.event_type == EventType.AWAY_STARTED:
            away_count += 1

        self._focus_total += focus_estimate.focus_score
        self._focus_count += 1
        average_focus = self._focus_total / self._focus_count
        max_focus = focus_estimate.focus_score if self._focus_count == 1 else max(summary.max_focus_score, focus_estimate.focus_score)
        min_focus = focus_estimate.focus_score if self._focus_count == 1 else min(summary.min_focus_score, focus_estimate.focus_score)

        self._summary = AnalysisSummary(
            total_duration_sec=round(total_duration, 3),
            total_present_duration_sec=round(snapshot.total_present_duration_sec, 3),
            total_away_duration_sec=round(snapshot.total_away_duration_sec, 3),
            total_studying_duration_sec=round(snapshot.total_studying_duration_sec, 3),
            away_count=away_count,
            average_focus_score=round(average_focus, 2),
            max_focus_score=round(max_focus, 2),
            min_focus_score=round(min_focus, 2),
            focus_samples=self._focus_count,
        )
        return self._summary
