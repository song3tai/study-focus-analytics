"""Single-frame scene feature extraction for behavior analysis."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import BBox, Detection, DetectionResult, FrameFeatures, FramePacket, ROI


@dataclass(slots=True)
class SceneFeatureExtractor:
    """Convert detector output into behavior-ready single-frame features."""

    roi_overlap_threshold: float = 0.2
    motion_norm: float = 100.0

    def extract(
        self,
        frame_packet: FramePacket,
        detection_result: DetectionResult,
        roi: ROI,
        prev_features: FrameFeatures | None = None,
    ) -> FrameFeatures:
        primary_detection = self._select_primary_person(detection_result)
        primary_bbox = primary_detection.bbox if primary_detection is not None else None

        roi_overlap_ratio = self._compute_roi_overlap_ratio(primary_bbox, roi)
        person_in_roi = roi_overlap_ratio >= self.roi_overlap_threshold
        motion_delta = self._compute_motion_delta(primary_bbox, prev_features)
        stability_score = self._compute_stability_score(motion_delta)

        return FrameFeatures(
            frame_id=frame_packet.frame_id,
            timestamp=frame_packet.timestamp,
            person_detected=primary_detection is not None,
            person_in_roi=person_in_roi,
            primary_detection=primary_detection,
            primary_bbox=primary_bbox,
            bbox_center_x=primary_bbox.center[0] if primary_bbox is not None else None,
            bbox_center_y=primary_bbox.center[1] if primary_bbox is not None else None,
            bbox_area=float(primary_bbox.area) if primary_bbox is not None else 0.0,
            bbox_aspect_ratio=self._compute_aspect_ratio(primary_bbox),
            roi_overlap_ratio=roi_overlap_ratio,
            motion_delta=motion_delta,
            stability_score=stability_score,
        )

    def _select_primary_person(self, detection_result: DetectionResult) -> Detection | None:
        return detection_result.primary_person

    def _compute_roi_overlap_ratio(self, primary_bbox: BBox | None, roi: ROI) -> float:
        if primary_bbox is None:
            return 0.0
        return primary_bbox.overlap_ratio(roi.to_bbox())

    def _compute_motion_delta(
        self,
        primary_bbox: BBox | None,
        prev_features: FrameFeatures | None,
    ) -> float:
        if primary_bbox is None or prev_features is None or prev_features.primary_bbox is None:
            return 0.0

        current_center_x, current_center_y = primary_bbox.center
        prev_center_x, prev_center_y = prev_features.primary_bbox.center
        delta_x = current_center_x - prev_center_x
        delta_y = current_center_y - prev_center_y
        return (delta_x**2 + delta_y**2) ** 0.5

    def _compute_stability_score(self, motion_delta: float) -> float:
        if self.motion_norm <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (motion_delta / self.motion_norm)))

    @staticmethod
    def _compute_aspect_ratio(primary_bbox: BBox | None) -> float:
        if primary_bbox is None or primary_bbox.height <= 0:
            return 0.0
        return primary_bbox.width / float(primary_bbox.height)
