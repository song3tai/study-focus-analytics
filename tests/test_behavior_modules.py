from __future__ import annotations

import numpy as np

from src.behavior.focus_estimator import FocusEstimator
from src.behavior.scene_features import SceneFeatureExtractor
from src.behavior.state_tracker import StateTracker, StateTrackerConfig
from src.core.enums import BehaviorState, FocusLevel, SourceType
from src.core.models import BBox, BehaviorStateSnapshot, Detection, DetectionResult, FrameFeatures, FramePacket, ROI


def _frame_packet(frame_id: int, timestamp: float) -> FramePacket:
    return FramePacket(
        frame_id=frame_id,
        timestamp=timestamp,
        source_type=SourceType.FILE,
        source_name="test.mp4",
        is_live=False,
        frame=np.zeros((100, 100, 3), dtype=np.uint8),
        fps_hint=10.0,
    )


def _person_detection_result(frame_id: int, timestamp: float, bbox: BBox) -> DetectionResult:
    return DetectionResult(
        frame_id=frame_id,
        timestamp=timestamp,
        detections=[
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.95,
                bbox=bbox,
            )
        ],
        inference_ms=5.0,
        model_name="fake-yolo",
    )


def _snapshot(state: BehaviorState) -> BehaviorStateSnapshot:
    return BehaviorStateSnapshot(
        frame_id=1,
        timestamp=1.0,
        current_state=state,
    )


def test_scene_feature_extractor_marks_person_inside_roi() -> None:
    extractor = SceneFeatureExtractor(roi_overlap_threshold=0.2, motion_norm=100.0)
    roi = ROI(x=20, y=20, w=60, h=70)
    bbox = BBox(x1=30, y1=30, x2=70, y2=85)

    features = extractor.extract(
        frame_packet=_frame_packet(frame_id=1, timestamp=0.1),
        detection_result=_person_detection_result(frame_id=1, timestamp=0.1, bbox=bbox),
        roi=roi,
    )

    assert features.person_detected is True
    assert features.person_in_roi is True
    assert features.primary_bbox == bbox
    assert features.roi_overlap_ratio > 0.8
    assert features.stability_score == 1.0


def test_state_tracker_debounces_and_tracks_durations() -> None:
    tracker = StateTracker(
        config=StateTrackerConfig(
            to_away_sec=0.5,
            away_to_present_sec=0.5,
            present_to_studying_sec=1.0,
            studying_to_present_sec=0.5,
            studying_stability_threshold=0.7,
            studying_motion_threshold=20.0,
        )
    )

    sequence = [
        (0.0, True, True, 0.9, 40.0),
        (0.6, True, True, 0.9, 35.0),
        (1.2, True, True, 0.95, 0.0),
        (2.4, True, True, 0.95, 0.0),
        (3.0, False, False, 0.0, 0.0),
        (3.7, False, False, 0.0, 0.0),
        (4.3, False, False, 0.0, 0.0),
    ]

    snapshots = []
    for frame_id, (timestamp, person_detected, person_in_roi, stability_score, motion_delta) in enumerate(sequence):
        snapshots.append(
            tracker.update(
                features=FrameFeatures(
                    frame_id=frame_id,
                    timestamp=timestamp,
                    person_detected=person_detected,
                    person_in_roi=person_in_roi,
                    roi_overlap_ratio=0.9 if person_in_roi else 0.0,
                    stability_score=stability_score,
                    motion_delta=motion_delta,
                    primary_bbox=BBox(x1=30, y1=30, x2=70, y2=85) if person_detected else None,
                )
            )
        )

    assert snapshots[0].current_state == BehaviorState.UNKNOWN
    assert snapshots[1].current_state == BehaviorState.PRESENT
    assert snapshots[3].current_state == BehaviorState.STUDYING
    assert snapshots[5].current_state == BehaviorState.AWAY
    assert snapshots[6].away_count == 1
    assert snapshots[6].current_away_duration_sec > 0.0
    assert snapshots[6].total_present_duration_sec > 0.0
    assert snapshots[6].total_studying_duration_sec > 0.0
    assert snapshots[6].total_away_duration_sec > 0.0


def test_focus_estimator_reflects_state_and_feature_quality() -> None:
    estimator = FocusEstimator()

    away_features = FrameFeatures(
        frame_id=1,
        timestamp=1.0,
        person_detected=False,
        person_in_roi=False,
        roi_overlap_ratio=0.0,
        stability_score=0.0,
        motion_delta=0.0,
    )
    present_features = FrameFeatures(
        frame_id=2,
        timestamp=2.0,
        person_detected=True,
        person_in_roi=True,
        primary_bbox=BBox(x1=30, y1=30, x2=70, y2=85),
        roi_overlap_ratio=0.8,
        stability_score=0.6,
        motion_delta=0.2,
    )
    studying_features = FrameFeatures(
        frame_id=3,
        timestamp=3.0,
        person_detected=True,
        person_in_roi=True,
        primary_bbox=BBox(x1=30, y1=30, x2=70, y2=85),
        roi_overlap_ratio=0.95,
        stability_score=0.95,
        motion_delta=0.05,
    )

    away_focus = estimator.estimate(away_features, _snapshot(BehaviorState.AWAY))
    present_focus = estimator.estimate(present_features, _snapshot(BehaviorState.PRESENT))
    studying_focus = estimator.estimate(studying_features, _snapshot(BehaviorState.STUDYING))

    assert away_focus.focus_level == FocusLevel.LOW
    assert away_focus.focus_score < present_focus.focus_score < studying_focus.focus_score
    assert present_focus.subscores is not None
    assert set(present_focus.subscores) == {"state", "stability", "roi", "motion"}
    assert studying_focus.reasons
    assert "state=studying" in studying_focus.reasons
    assert "in_study_roi" in studying_focus.reasons
