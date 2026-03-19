"""Pydantic schemas for API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.core.models import AnalysisSummary, ProcessResult


class SummaryResponse(BaseModel):
    total_duration_sec: float
    total_present_duration_sec: float
    total_away_duration_sec: float
    total_studying_duration_sec: float
    away_count: int
    average_focus_score: float
    max_focus_score: float
    min_focus_score: float
    focus_samples: int

    @classmethod
    def from_summary(cls, summary: AnalysisSummary) -> "SummaryResponse":
        return cls(**summary.__dict__)


class ProcessResultResponse(BaseModel):
    payload: dict[str, Any]

    @classmethod
    def from_result(cls, result: ProcessResult) -> "ProcessResultResponse":
        return cls(payload=result.to_dict())
