"""Shared enums used across the analysis pipeline."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Backport-style string enum base for JSON-friendly values."""


class BehaviorState(StrEnum):
    UNKNOWN = "unknown"
    PRESENT = "present"
    AWAY = "away"
    STUDYING = "studying"


class FocusLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventType(StrEnum):
    STATE_CHANGED = "state_changed"
    AWAY_STARTED = "away_started"
    AWAY_ENDED = "away_ended"
    STUDYING_STARTED = "studying_started"
    STUDYING_ENDED = "studying_ended"


class SourceType(StrEnum):
    FILE = "file"
    CAMERA = "camera"
    RTSP = "rtsp"

