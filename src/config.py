"""Centralized runtime defaults for Study Focus Analytics."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import ROI


@dataclass(frozen=True)
class AppConfig:
    """Default configuration values for CLI/runtime wiring."""

    default_mode: str = "analyze"
    output_filename: str = "processed_output.mp4"
    window_name: str = "study_focus_analytics"
    default_camera_index: int = 0
    fallback_fps: float = 30.0
    default_rtsp_url: str = "rtsp://192.168.3.3:8554/live"
    default_rtsp_transport: str = "auto"
    live_reconnect_attempts: int = 3
    live_reconnect_interval_sec: float = 1.0

    # YOLOv8 defaults
    yolo_model_name: str = "yolov8n.pt"
    yolo_conf_threshold: float = 0.35

    # ROI ratios
    roi_left_ratio: float = 0.2
    roi_top_ratio: float = 0.15
    roi_right_ratio: float = 0.8
    roi_bottom_ratio: float = 0.92

    # Behavior thresholds
    present_confirm_seconds: float = 1.0
    away_confirm_seconds: float = 2.0
    studying_confirm_seconds: float = 10.0
    studying_min_stability: float = 0.6
    focus_window_frames: int = 120
    max_recent_events: int = 100

    def build_roi(self, *, width: int, height: int) -> ROI:
        """Build the default study/work ROI from configured ratios."""
        x1 = int(width * self.roi_left_ratio)
        y1 = int(height * self.roi_top_ratio)
        x2 = int(width * self.roi_right_ratio)
        y2 = int(height * self.roi_bottom_ratio)
        return ROI(
            x=x1,
            y=y1,
            w=max(0, x2 - x1),
            h=max(0, y2 - y1),
        )
