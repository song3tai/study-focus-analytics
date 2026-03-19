from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.core.enums import SourceType, BehaviorState, FocusLevel, EventType


# Geometry models


@dataclass(slots=True)
class BBox:
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

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.width / 2.0, self.y1 + self.height / 2.0)

    def to_xyxy(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2, self.y2

    def intersection(self, other: "BBox | ROI") -> "BBox | None":
        other_bbox = other.to_bbox() if isinstance(other, ROI) else other
        x1 = max(self.x1, other_bbox.x1)
        y1 = max(self.y1, other_bbox.y1)
        x2 = min(self.x2, other_bbox.x2)
        y2 = min(self.y2, other_bbox.y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return BBox(x1=x1, y1=y1, x2=x2, y2=y2)

    def overlap_ratio(self, other: "BBox | ROI") -> float:
        overlap = self.intersection(other)
        if overlap is None or self.area <= 0:
            return 0.0
        return overlap.area / float(self.area)

    def to_dict(self) -> dict[str, Any]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
            "area": self.area,
            "center": self.center,
        }


@dataclass(slots=True)
class ROI:
    x: int
    y: int
    w: int
    h: int
    name: str = "study_area"

    @property
    def x1(self) -> int:
        return self.x

    @property
    def y1(self) -> int:
        return self.y

    @property
    def x2(self) -> int:
        return self.x + max(0, self.w)

    @property
    def y2(self) -> int:
        return self.y + max(0, self.h)

    @property
    def width(self) -> int:
        return max(0, self.w)

    @property
    def height(self) -> int:
        return max(0, self.h)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)

    def to_bbox(self) -> BBox:
        return BBox(x1=self.x1, y1=self.y1, x2=self.x2, y2=self.y2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "name": self.name,
            "x2": self.x2,
            "y2": self.y2,
            "center": self.center,
        }


# Input and detection models


@dataclass(slots=True)
class FramePacket:
    frame_id: int
    timestamp: float
    source_type: SourceType
    source_name: str
    is_live: bool
    frame: np.ndarray
    fps_hint: float | None = None

    @property
    def frame_shape(self) -> tuple[int, ...]:
        return tuple(self.frame.shape)

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "is_live": self.is_live,
            "fps_hint": self.fps_hint,
            "frame_shape": self.frame_shape,
        }


@dataclass(slots=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: BBox
    track_id: int | None = None

    @property
    def label(self) -> str:
        return self.class_name

    @property
    def center(self) -> tuple[float, float]:
        return self.bbox.center

    @property
    def area(self) -> int:
        return self.bbox.area

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "track_id": self.track_id,
        }


@dataclass(slots=True)
class DetectionResult:
    frame_id: int
    timestamp: float
    detections: list[Detection] = field(default_factory=list)
    inference_ms: float = 0.0
    model_name: str = ""

    @property
    def person_detections(self) -> list[Detection]:
        return [det for det in self.detections if det.class_name.lower() == "person"]

    @property
    def has_person(self) -> bool:
        return bool(self.person_detections)

    @property
    def primary_person(self) -> Detection | None:
        if not self.person_detections:
            return None
        return max(self.person_detections, key=lambda det: det.area)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "detections": [det.to_dict() for det in self.detections],
            "inference_ms": self.inference_ms,
            "model_name": self.model_name,
            "has_person": self.has_person,
        }


# Behavior analysis models


@dataclass(slots=True)
class FrameFeatures:
    frame_id: int
    timestamp: float
    person_detected: bool
    person_in_roi: bool
    primary_detection: Detection | None = None
    primary_bbox: BBox | None = None
    bbox_center_x: float | None = None
    bbox_center_y: float | None = None
    bbox_area: float = 0.0
    bbox_aspect_ratio: float = 0.0
    roi_overlap_ratio: float = 0.0
    motion_delta: float = 0.0
    stability_score: float = 0.0

    def __post_init__(self) -> None:
        if self.primary_bbox is None and self.primary_detection is not None:
            self.primary_bbox = self.primary_detection.bbox
        if self.primary_bbox is not None:
            if self.bbox_center_x is None or self.bbox_center_y is None:
                center_x, center_y = self.primary_bbox.center
                self.bbox_center_x = center_x
                self.bbox_center_y = center_y
            if self.bbox_area == 0.0:
                self.bbox_area = float(self.primary_bbox.area)
            if self.bbox_aspect_ratio == 0.0 and self.primary_bbox.height > 0:
                self.bbox_aspect_ratio = self.primary_bbox.width / float(self.primary_bbox.height)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "person_detected": self.person_detected,
            "person_in_roi": self.person_in_roi,
            "primary_detection": self.primary_detection.to_dict() if self.primary_detection else None,
            "primary_bbox": self.primary_bbox.to_dict() if self.primary_bbox else None,
            "bbox_center_x": self.bbox_center_x,
            "bbox_center_y": self.bbox_center_y,
            "bbox_area": self.bbox_area,
            "bbox_aspect_ratio": self.bbox_aspect_ratio,
            "roi_overlap_ratio": self.roi_overlap_ratio,
            "motion_delta": self.motion_delta,
            "stability_score": self.stability_score,
        }


@dataclass(slots=True)
class BehaviorStateSnapshot:
    frame_id: int
    timestamp: float
    current_state: BehaviorState
    previous_state: BehaviorState | None = None
    candidate_state: BehaviorState | None = None
    candidate_duration_sec: float = 0.0
    state_duration_sec: float = 0.0
    current_session_duration_sec: float = 0.0
    current_away_duration_sec: float = 0.0
    total_present_duration_sec: float = 0.0
    total_away_duration_sec: float = 0.0
    total_studying_duration_sec: float = 0.0
    away_count: int = 0
    is_state_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state is not None else None,
            "candidate_state": self.candidate_state.value if self.candidate_state is not None else None,
            "candidate_duration_sec": self.candidate_duration_sec,
            "state_duration_sec": self.state_duration_sec,
            "current_session_duration_sec": self.current_session_duration_sec,
            "current_away_duration_sec": self.current_away_duration_sec,
            "total_present_duration_sec": self.total_present_duration_sec,
            "total_away_duration_sec": self.total_away_duration_sec,
            "total_studying_duration_sec": self.total_studying_duration_sec,
            "away_count": self.away_count,
            "is_state_changed": self.is_state_changed,
        }


@dataclass(slots=True)
class FocusEstimate:
    frame_id: int
    timestamp: float
    focus_score: float
    focus_level: FocusLevel
    reasons: list[str] = field(default_factory=list)
    subscores: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "focus_score": self.focus_score,
            "focus_level": self.focus_level.value,
            "reasons": list(self.reasons),
            "subscores": dict(self.subscores) if self.subscores is not None else None,
        }


@dataclass(slots=True)
class BehaviorEvent:
    event_type: EventType
    timestamp: float
    frame_id: int
    state_before: BehaviorState | None = None
    state_after: BehaviorState | None = None
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "state_before": self.state_before.value if self.state_before is not None else None,
            "state_after": self.state_after.value if self.state_after is not None else None,
            "message": self.message,
            "payload": dict(self.payload),
        }


# Summary models


@dataclass(slots=True)
class AnalysisSummary:
    total_duration_sec: float = 0.0
    total_present_duration_sec: float = 0.0
    total_away_duration_sec: float = 0.0
    total_studying_duration_sec: float = 0.0
    away_count: int = 0
    average_focus_score: float = 0.0
    max_focus_score: float = 0.0
    min_focus_score: float = 0.0
    focus_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_duration_sec": self.total_duration_sec,
            "total_present_duration_sec": self.total_present_duration_sec,
            "total_away_duration_sec": self.total_away_duration_sec,
            "total_studying_duration_sec": self.total_studying_duration_sec,
            "away_count": self.away_count,
            "average_focus_score": self.average_focus_score,
            "max_focus_score": self.max_focus_score,
            "min_focus_score": self.min_focus_score,
            "focus_samples": self.focus_samples,
        }


# End-to-end pipeline result


@dataclass(slots=True)
class ProcessResult:
    frame_packet: FramePacket
    detection_result: DetectionResult | None = None
    frame_features: FrameFeatures | None = None
    state_snapshot: BehaviorStateSnapshot | None = None
    focus_estimate: FocusEstimate | None = None
    events: list[BehaviorEvent] = field(default_factory=list)
    rendered_frame: np.ndarray | None = None
    summary: AnalysisSummary | None = None
    error_message: str | None = None

    @property
    def frame_id(self) -> int:
        return self.frame_packet.frame_id

    @property
    def timestamp(self) -> float:
        return self.frame_packet.timestamp

    @property
    def event(self) -> BehaviorEvent | None:
        return self.events[0] if self.events else None

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "frame_packet": self.frame_packet.to_meta_dict(),
            "detection_result": self.detection_result.to_dict() if self.detection_result else None,
            "frame_features": self.frame_features.to_dict() if self.frame_features else None,
            "state_snapshot": self.state_snapshot.to_dict() if self.state_snapshot else None,
            "focus_estimate": self.focus_estimate.to_dict() if self.focus_estimate else None,
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary.to_dict() if self.summary else None,
            "error_message": self.error_message,
            "has_rendered_frame": self.rendered_frame is not None,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_meta_dict()
