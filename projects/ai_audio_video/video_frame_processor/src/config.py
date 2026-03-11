"""Centralized runtime defaults for video_frame_processor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Default configuration values for CLI/runtime wiring."""

    default_mode: str = "original"
    output_filename: str = "processed_output.mp4"
    window_name: str = "video_frame_processor"

    # YOLOv8 defaults
    yolo_model_name: str = "yolov8n.pt"
    yolo_conf_threshold: float = 0.35
