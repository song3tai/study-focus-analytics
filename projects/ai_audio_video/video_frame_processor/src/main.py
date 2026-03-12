"""CLI entrypoint for video_frame_processor."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_detector import AIDetector
from config import AppConfig
from frame_processor import FrameProcessor, SUPPORTED_MODES
from pipeline import VideoPipeline
from utils import ensure_dir, project_root, resolve_input_path
from video_reader import create_frame_source
from video_writer import VideoWriter


def parse_args(config: AppConfig) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Video frame processor")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input",
        help="Input video path or filename in project input/ directory",
    )
    source_group.add_argument(
        "--rtsp-url",
        nargs="?",
        const=config.default_rtsp_url,
        default=None,
        help=f"RTSP stream URL (default when flag is present without value: {config.default_rtsp_url})",
    )
    source_group.add_argument(
        "--camera",
        action="store_true",
        help="Use camera input instead of a video file",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=config.default_camera_index,
        help="Camera device index used with --camera",
    )
    parser.add_argument(
        "--mode",
        default=config.default_mode,
        choices=SUPPORTED_MODES + ("detect",),
        help="Frame processing mode",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save processed output video",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable preview window (useful in headless environments)",
    )
    parser.add_argument(
        "--model",
        default=config.yolo_model_name,
        help="YOLO model name/path used in detect mode",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=config.yolo_conf_threshold,
        help="YOLO confidence threshold for detect mode",
    )
    parser.add_argument(
        "--rtsp-transport",
        choices=("auto", "tcp", "udp"),
        default=config.default_rtsp_transport,
        help="RTSP transport protocol for live streams",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output file path (default: output/processed_output.mp4)",
    )
    return parser.parse_args()


def build_output_path(root: Path, config: AppConfig, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg).expanduser().resolve(strict=False)
    return (root / "output" / config.output_filename).resolve(strict=False)


def main() -> int:
    config = AppConfig()
    args = parse_args(config)

    root = project_root()
    input_path = None
    if args.input:
        input_path = resolve_input_path(args.input, root)
        if not input_path.exists():
            print(f"[ERROR] Input video file not found: {input_path}")
            print("[TIP] Put a test video under input/ and pass its filename, e.g. --input sample.mp4")
            return 1

        if not input_path.is_file():
            print(f"[ERROR] Input path is not a file: {input_path}")
            return 1

    is_live_source = args.camera or bool(args.rtsp_url)
    if is_live_source and args.save:
        print("[ERROR] Saving live camera/RTSP output is not supported yet. Remove --save for live sources.")
        return 1

    try:
        reader = create_frame_source(
            input_path=input_path,
            use_camera=args.camera,
            camera_index=args.camera_index,
            rtsp_url=args.rtsp_url,
            rtsp_transport=args.rtsp_transport,
            fallback_fps=config.fallback_fps,
        )
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1

    frame_processor = FrameProcessor()

    writer = None
    if args.save:
        output_path = build_output_path(root, config, args.output)
        ensure_dir(output_path.parent)
        width, height = reader.frame_size()
        fps = reader.fps()
        writer = VideoWriter(output_path=output_path, width=width, height=height, fps=fps)
        print(f"[INFO] Saving processed video to: {output_path}")

    detector = None
    if args.mode == "detect":
        detector = AIDetector(model_name=args.model, conf_threshold=args.conf)

    pipeline = VideoPipeline(
        reader=reader,
        frame_processor=frame_processor,
        config=config,
        mode=args.mode,
        display_enabled=not args.no_display,
        writer=writer,
        detector=detector,
    )
    return pipeline.run()


if __name__ == "__main__":
    raise SystemExit(main())
