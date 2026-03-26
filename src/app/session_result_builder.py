"""Helpers for finalizing session-level analysis results."""

from __future__ import annotations

from src.core.models import SessionResult
from src.pipeline import LocalAnalysisPipeline


def finalize_session_result(pipeline: LocalAnalysisPipeline) -> SessionResult:
    """Finalize one pipeline session into a SessionResult."""
    return pipeline.build_session_result()
