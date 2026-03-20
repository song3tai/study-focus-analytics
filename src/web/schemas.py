"""Pydantic schemas for the web boundary."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    api_version: str


class StartAnalysisRequest(BaseModel):
    source_type: Literal["camera", "video_file", "rtsp"]
    source: str | None = None
    debug: bool = False


class SimpleMessageResponse(BaseModel):
    success: bool
    message: str
    session_state: str


class AnalysisStatusResponse(BaseModel):
    running: bool
    session_state: str
    source_type: str | None = None
    source: str | None = None
    started_at: str | None = None
    has_latest_result: bool
    last_frame_id: int | None = None
    last_timestamp: float | None = None
    last_error: str | None = None

    @classmethod
    def from_status_payload(cls, payload: Mapping[str, Any]) -> "AnalysisStatusResponse":
        return cls(**dict(payload))


class LatestResultResponse(BaseModel):
    has_result: bool
    data: dict[str, Any] | None = None
    message: str = ""


class SummaryEnvelopeResponse(BaseModel):
    has_summary: bool
    data: dict[str, Any] | None = None
    message: str = ""


class WebSocketEnvelope(BaseModel):
    type: Literal["process_result", "service_status", "service_error"]
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    data: dict[str, Any]
