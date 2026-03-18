from __future__ import annotations

import numpy as np

from src.behavior.analytics_aggregator import AnalyticsAggregator
from src.behavior.event_builder import EventBuilder
from src.behavior.focus_estimator import FocusEstimator
from src.behavior.scene_features import SceneFeatureExtractor
from src.behavior.state_tracker import StateTracker
from src.core.enums import BehaviorState, EventType, FocusLevel, SourceType
from src.core.models import Detection, DetectionResult, FrameFeatures, FramePacket, ROI


def _frame_packet(frame_index: int, timestamp_seconds: float) -> FramePacket:
    return FramePacket(
        frame=np.zeros((100, 100, 3), dtype=np.uint8),
        frame_index=frame_index,
        timestamp_seconds=timestamp_seconds,
        source_type=SourceType.FILE,
        source_label="test.mp4",
    )


def test_scene_feature_extractor_marks_person_inside_roi() -> None:
    extractor = SceneFeatureExtractor(roi=ROI(x1=20, y1=20, x2=80, y2=90))
    packet = _frame_packet(frame_index=1, timestamp_seconds=0.1)
    detections = DetectionResult(
        frame_index=1,
        timestamp_seconds=0.1,
        detections=[Detection(label="person", confidence=0.9, bbox=ROI(x1=30, y1=30, x2=70, y2=85))],
    )

    features = extractor.extract(packet, detections)

    assert features.person_detected is True
    assert features.person_in_roi is True
    assert features.roi_overlap_ratio > 0.8


def test_state_tracker_debounces_and_enters_studying() -> None:
    tracker = StateTracker(
        present_confirm_seconds=0.5,
        away_confirm_seconds=0.5,
        studying_confirm_seconds=2.0,
        studying_min_stability=0.6,
    )

    timestamps = [0.0, 0.5, 1.0, 2.5]
    snapshots = []
    for index, timestamp in enumerate(timestamps):
        snapshots.append(
            tracker.update(
                FrameFeatures(
                    frame_index=index,
                    timestamp_seconds=timestamp,
                    roi=ROI(x1=20, y1=20, x2=80, y2=90),
                    person_detected=True,
                    person_in_roi=True,
                    roi_overlap_ratio=0.9,
                    bbox_area_ratio=0.2,
                    motion_score=0.05,
                    stability_score=0.9,
                    person_bbox=ROI(x1=30, y1=30, x2=70, y2=85),
                )
            )
        )

    assert snapshots[0].state == BehaviorState.UNKNOWN
    assert snapshots[1].state == BehaviorState.PRESENT
    assert snapshots[-1].state == BehaviorState.STUDYING


def test_focus_event_and_summary_modules_work_together() -> None:
    tracker = StateTracker(present_confirm_seconds=0.0, away_confirm_seconds=0.0, studying_confirm_seconds=1.0)
    focus_estimator = FocusEstimator()
    event_builder = EventBuilder()
    aggregator = AnalyticsAggregator()

    latest_event = None
    latest_focus = None
    latest_snapshot = None
    for index, timestamp in enumerate([0.0, 0.5, 1.5]):
        features = FrameFeatures(
            frame_index=index,
            timestamp_seconds=timestamp,
            roi=ROI(x1=20, y1=20, x2=80, y2=90),
            person_detected=True,
            person_in_roi=True,
            roi_overlap_ratio=0.9,
            bbox_area_ratio=0.2,
            motion_score=0.02,
            stability_score=0.95,
            person_bbox=ROI(x1=30, y1=30, x2=70, y2=85),
        )
        latest_snapshot = tracker.update(features)
        latest_focus = focus_estimator.estimate(latest_snapshot, features)
        latest_event = event_builder.build(latest_snapshot) or latest_event
        summary = aggregator.update(latest_snapshot, latest_focus, event_builder.build(latest_snapshot))

    assert latest_snapshot is not None
    assert latest_snapshot.state == BehaviorState.STUDYING
    assert latest_focus is not None
    assert latest_focus.focus_level in {FocusLevel.MEDIUM, FocusLevel.HIGH}
    assert latest_event is not None
    assert latest_event.event_type in {EventType.STATE_CHANGED, EventType.STUDYING_STARTED}
    assert summary.studying_duration_seconds > 0.0
