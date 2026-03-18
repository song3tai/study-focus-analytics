"""Convert detector output into behavior-oriented scene features."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import DetectionResult, FrameFeatures, FramePacket, ROI


@dataclass
class SceneFeatureExtractor:
    """Extract simple, explainable features from single-person detections."""

    roi: ROI
    _last_center: tuple[float, float] | None = None

    def extract(self, frame_packet: FramePacket, detection_result: DetectionResult) -> FrameFeatures:
        frame_height, frame_width = frame_packet.frame.shape[:2]
        primary_person = detection_result.primary_person

        if primary_person is None:
            self._last_center = None
            return FrameFeatures(
                frame_index=frame_packet.frame_index,
                timestamp_seconds=frame_packet.timestamp_seconds,
                roi=self.roi,
                person_detected=False,
                person_in_roi=False,
                roi_overlap_ratio=0.0,
                bbox_area_ratio=0.0,
                motion_score=1.0,
                stability_score=0.0,
            )

        bbox = primary_person.bbox
        roi_overlap_ratio = bbox.overlap_ratio(self.roi)
        bbox_area_ratio = bbox.area / float(max(1, frame_height * frame_width))
        center = primary_person.center

        motion_score = 0.0
        if self._last_center is not None:
            delta_x = center[0] - self._last_center[0]
            delta_y = center[1] - self._last_center[1]
            diagonal = max(1.0, (frame_width**2 + frame_height**2) ** 0.5)
            motion_score = min(1.0, ((delta_x**2 + delta_y**2) ** 0.5) / diagonal)
        self._last_center = center

        stability_score = max(0.0, min(1.0, (roi_overlap_ratio * 0.7) + ((1.0 - motion_score) * 0.3)))

        return FrameFeatures(
            frame_index=frame_packet.frame_index,
            timestamp_seconds=frame_packet.timestamp_seconds,
            roi=self.roi,
            person_detected=True,
            person_in_roi=roi_overlap_ratio > 0.25,
            roi_overlap_ratio=roi_overlap_ratio,
            bbox_area_ratio=bbox_area_ratio,
            motion_score=motion_score,
            stability_score=stability_score,
            person_bbox=bbox,
        )
