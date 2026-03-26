"""Application-level runners for offline analysis tasks."""

from __future__ import annotations

from src.app.session_result_builder import finalize_session_result
from src.config import AppConfig
from src.core.enums import AnalysisMode, SourceType
from src.core.models import FramePacket, SessionResult
from src.inference.ai_detector import AIDetector
from src.io.video_reader import create_frame_source
from src.pipeline import LocalAnalysisPipeline, PipelineConfig
from src.pipeline.analysis_pipeline import calculate_timestamp_seconds
from src.utils import project_root, resolve_input_path


def run_fast_analysis(source: str) -> SessionResult:
    """Run a file-backed analysis session as fast as possible and return its final result."""
    config = AppConfig()
    input_path = resolve_input_path(source, project_root())
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f"video file not found: {input_path}")

    reader = create_frame_source(
        input_path=input_path,
        use_camera=False,
        camera_index=config.default_camera_index,
        rtsp_url=None,
        rtsp_transport=config.default_rtsp_transport,
        fallback_fps=config.fallback_fps,
    )

    try:
        detector = AIDetector(
            model_name=config.yolo_model_name,
            conf_threshold=config.yolo_conf_threshold,
        )
        width, height = reader.frame_size()
        roi = config.build_roi(width=width, height=height)
        pipeline = LocalAnalysisPipeline(
            roi=roi,
            config=PipelineConfig(enable_debug_logging=False),
            analysis_mode=AnalysisMode.FAST,
        )
        pipeline.reset()

        frame_index = 0
        source_fps = reader.fps()
        started_monotonic = 0.0
        while True:
            ok, frame = reader.read_frame()
            if not ok or frame is None:
                break

            timestamp_seconds = calculate_timestamp_seconds(
                frame_index=frame_index,
                source_fps=source_fps,
                is_live=False,
                started_monotonic=started_monotonic,
            )
            frame_packet = FramePacket(
                frame_id=frame_index,
                timestamp=timestamp_seconds,
                source_type=SourceType.FILE,
                source_name=getattr(reader, "source_label", str(input_path)),
                is_live=False,
                frame=frame,
                fps_hint=source_fps,
            )
            detection_result = detector.detect_frame(
                frame,
                frame_index=frame_index,
                timestamp_seconds=timestamp_seconds,
            )
            pipeline.process_frame(
                frame_packet=frame_packet,
                detection_result=detection_result,
            )
            frame_index += 1

        return finalize_session_result(pipeline)
    finally:
        reader.release()
