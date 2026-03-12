"""Centralized runtime defaults for video_frame_processor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Default configuration values for CLI/runtime wiring."""

    default_mode: str = "original"
    output_filename: str = "processed_output.mp4"
    window_name: str = "video_frame_processor"
    default_camera_index: int = 0
    fallback_fps: float = 30.0
    default_rtsp_url: str = "rtsp://192.168.3.3:8554/live"
    default_rtsp_transport: str = "auto"
    live_reconnect_attempts: int = 3
    live_reconnect_interval_sec: float = 1.0

    # YOLOv8 defaults
    yolo_model_name: str = "yolov8n.pt"
    yolo_conf_threshold: float = 0.35
