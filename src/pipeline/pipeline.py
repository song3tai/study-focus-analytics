"""Backward-compatible pipeline re-exports.

Formal pipeline implementations live in ``src.pipeline.analysis_pipeline``.
This module remains as a thin compatibility layer so older imports do not
keep a second pipeline implementation alive.
"""

from __future__ import annotations

from src.pipeline.analysis_pipeline import LocalAnalysisPipeline, PipelineConfig

__all__ = ["LocalAnalysisPipeline", "PipelineConfig"]
