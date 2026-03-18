"""Structured models shared by inference, behavior, pipeline, and web layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.core.enums import BehaviorState, EventType, FocusLevel, SourceType


@dataclass(frozen=True)
class ROI:
    """Pixel-based rectangular region of interest."""

    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def intersection(self, other: "ROI") -> "ROI | None":
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return ROI(x1=x1, y1=y1, x2=x2, y2=y2)

    def overlap_ratio(self, other: "ROI") -> float:
        overlap = self.intersection(other)
        if overlap is None or self.area <= 0:
            return 0.0
        return overlap.area / float(self.area)


@dataclass(frozen=True)
class FramePacket:
    """One source frame with metadata."""

    frame: np.ndarray
    frame_index: int
    timestamp_seconds: float
    source_type: SourceType
    source_label: str


@dataclass(frozen=True)
class Detection:
    """A single structured detection."""

    label: str
    confidence: float
    bbox: ROI

    @property
    def center(self) -> tuple[float, float]:
        return self.bbox.center()

    @property
    def area(self) -> int:
        return self.bbox.area


@dataclass(frozen=True)
class DetectionResult:
    """Structured detector output for one frame."""

    frame_index: int
    timestamp_seconds: float
    detections: list[Detection] = field(default_factory=list)
    inference_ms: float = 0.0

    @property
    def primary_person(self) -> Detection | None:
        persons = [detection for detection in self.detections if detection.label == "person"]
        if not persons:
            return None
        return max(persons, key=lambda detection: detection.area)


@dataclass(frozen=True)
class FrameFeatures:
    """Behavior-ready features derived from detector output."""

    frame_index: int
    timestamp_seconds: float
    roi: ROI
    person_detected: bool
    person_in_roi: bool
    roi_overlap_ratio: float
    bbox_area_ratio: float
    motion_score: float
    stability_score: float
    person_bbox: ROI | None = None


@dataclass(frozen=True)
class BehaviorStateSnapshot:
    """Current state tracker snapshot."""

    frame_index: int
    timestamp_seconds: float
    state: BehaviorState
    previous_state: BehaviorState | None
    state_since_seconds: float
    state_duration_seconds: float
    continuous_presence_seconds: float
    person_in_roi: bool
    stability_score: float


@dataclass(frozen=True)
class FocusEstimate:
    """Explainable focus estimate for the current frame/window."""

    focus_score: float
    focus_level: FocusLevel
    reasons: list[str]


@dataclass(frozen=True)
class BehaviorEvent:
    """Discrete event emitted from state transitions."""

    event_type: EventType
    frame_index: int
    timestamp_seconds: float
    state: BehaviorState
    message: str


@dataclass(frozen=True)
class AnalysisSummary:
    """Session-level accumulated analytics."""

    total_duration_seconds: float = 0.0
    present_duration_seconds: float = 0.0
    away_duration_seconds: float = 0.0
    studying_duration_seconds: float = 0.0
    unknown_duration_seconds: float = 0.0
    away_count: int = 0
    event_count: int = 0
    average_focus_score: float = 0.0
    max_focus_score: float = 0.0
    min_focus_score: float = 0.0
    current_state: BehaviorState = BehaviorState.UNKNOWN


@dataclass(frozen=True)
class ProcessResult:
    """End-to-end structured result for one frame."""

    frame_packet: FramePacket
    detection_result: DetectionResult
    frame_features: FrameFeatures
    state_snapshot: BehaviorStateSnapshot
    focus_estimate: FocusEstimate
    summary: AnalysisSummary
    event: BehaviorEvent | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        def _convert(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, np.ndarray):
                return f"<ndarray shape={value.shape}>"
            if isinstance(value, dict):
                return {key: _convert(item) for key, item in value.items()}
            if isinstance(value, list):
                return [_convert(item) for item in value]
            if hasattr(value, "__dataclass_fields__"):
                return _convert(asdict(value))
            return value

        return _convert(asdict(self))
