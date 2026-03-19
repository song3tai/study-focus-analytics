"""Core enums shared across the Study Focus Analytics project."""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Input source type."""

    CAMERA = "camera"
    RTSP = "rtsp"
    FILE = "file"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class BehaviorState(str, Enum):
    """Behavior state machine states."""

    UNKNOWN = "unknown"
    PRESENT = "present"
    AWAY = "away"
    STUDYING = "studying"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class FocusLevel(str, Enum):
    """Focus score level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class EventType(str, Enum):
    """System event types."""

    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    AWAY_STARTED = "away_started"
    AWAY_ENDED = "away_ended"
    FOCUS_DROP = "focus_drop"
    FOCUS_RECOVERED = "focus_recovered"
    STREAM_DISCONNECTED = "stream_disconnected"
    STREAM_RECONNECTED = "stream_reconnected"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]
