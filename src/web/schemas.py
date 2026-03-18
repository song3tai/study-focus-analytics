"""Pydantic schemas for API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.core.models import AnalysisSummary, ProcessResult


class SummaryResponse(BaseModel):
    total_duration_seconds: float
    present_duration_seconds: float
    away_duration_seconds: float
    studying_duration_seconds: float
    unknown_duration_seconds: float
    away_count: int
    event_count: int
    average_focus_score: float
    max_focus_score: float
    min_focus_score: float
    current_state: str

    @classmethod
    def from_summary(cls, summary: AnalysisSummary) -> "SummaryResponse":
        return cls(**summary.__dict__, current_state=summary.current_state.value)


class ProcessResultResponse(BaseModel):
    payload: dict[str, Any]

    @classmethod
    def from_result(cls, result: ProcessResult) -> "ProcessResultResponse":
        return cls(payload=result.to_dict())
