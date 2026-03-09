"""Entry point for video_frame_processor v1.

Pipeline:
1) Read video frames
2) Process each frame
3) Display in real time
4) Optionally save output video
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2

from frame_processor import FrameProcessor, SUPPORTED_MODES
from utils import (
    create_video_writer,
    default_output_path,
    ensure_dir,
    project_root,
    resolve_input_path,
)
from video_reader import VideoReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Video frame processor v1")
    parser.add_argument(
        "--input",
        required=True,
        help="Input video path or filename in project input/ directory",
    )
    parser.add_argument(
        "--mode",
        default="original",
        choices=SUPPORTED_MODES,
        help="Frame processing mode",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save processed output to output/processed_output.mp4",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable preview window (useful in headless environments)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    input_path = resolve_input_path(args.input, root)
    display_enabled = not args.no_display

    if display_enabled and not os.environ.get("DISPLAY"):
        print("[WARN] DISPLAY is not available. Running without preview window.")
        display_enabled = False

    if not input_path.exists():
        print(f"[ERROR] Input video file not found: {input_path}")
        print("[TIP] Put a test video under input/ and pass its filename, e.g. --input sample.mp4")
        return 1

    if not input_path.is_file():
        print(f"[ERROR] Input path is not a file: {input_path}")
        return 1

    try:
        reader = VideoReader(input_path)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1

    processor = FrameProcessor()
    writer = None
    try:
        if args.save:
            output_dir = root / "output"
            ensure_dir(output_dir)
            output_path: Path = default_output_path(root)
            width, height = reader.frame_size()
            fps = reader.fps()
            writer = create_video_writer(output_path, width, height, fps)
            print(f"[INFO] Saving processed video to: {output_path}")

        while True:
            ok, frame = reader.read_frame()
            if not ok:
                break

            processed = processor.process_frame(frame, args.mode)
            if display_enabled:
                cv2.imshow("video_frame_processor", processed)

            if writer is not None:
                writer.write(processed)

            # Exit on ESC
            if display_enabled and cv2.waitKey(1) & 0xFF == 27:
                break
        return 0
    finally:
        reader.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
