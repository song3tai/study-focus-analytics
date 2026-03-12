"""Pipeline runner: read -> process/detect -> display -> save."""

from __future__ import annotations

import os
from time import sleep

import cv2

from ai_detector import AIDetector
from config import AppConfig
from frame_processor import FrameProcessor
from utils import FPSCounter, annotate_fps
from video_reader import FrameSource
from video_writer import VideoWriter


class VideoPipeline:
    """Coordinate frame reading, processing, visualization, and output writing."""

    def __init__(
        self,
        reader: FrameSource,
        frame_processor: FrameProcessor,
        config: AppConfig,
        mode: str,
        display_enabled: bool,
        writer: VideoWriter | None = None,
        detector: AIDetector | None = None,
    ) -> None:
        self.reader = reader
        self.frame_processor = frame_processor
        self.config = config
        self.mode = mode
        self.display_enabled = display_enabled
        self.writer = writer
        self.detector = detector
        self.fps_counter = FPSCounter()

    def run(self) -> int:
        display_enabled = self.display_enabled
        if display_enabled and not os.environ.get("DISPLAY"):
            print("[WARN] DISPLAY is not available. Running without preview window.")
            display_enabled = False

        try:
            while True:
                ok, frame = self.reader.read_frame()
                if not ok:
                    if self._attempt_live_reconnect():
                        continue
                    break

                output_frame = self._handle_frame(frame)
                annotate_fps(output_frame, self.fps_counter.tick())

                if display_enabled:
                    cv2.imshow(self.config.window_name, output_frame)

                if self.writer is not None:
                    self.writer.write_frame(output_frame)

                if display_enabled and cv2.waitKey(1) & 0xFF == 27:
                    break
            return 0
        finally:
            self.reader.release()
            if self.writer is not None:
                self.writer.release()
            cv2.destroyAllWindows()

    def _attempt_live_reconnect(self) -> bool:
        if not self.reader.is_live:
            return False

        for attempt in range(1, self.config.live_reconnect_attempts + 1):
            print(
                f"[WARN] Live stream frame read failed. Reconnecting "
                f"({attempt}/{self.config.live_reconnect_attempts})..."
            )
            if self.reader.reconnect():
                print("[INFO] Live stream reconnected.")
                return True
            if attempt < self.config.live_reconnect_attempts:
                sleep(self.config.live_reconnect_interval_sec)

        print("[ERROR] Live stream reconnect failed.")
        return False

    def _handle_frame(self, frame):
        if self.mode == "detect":
            if self.detector is None:
                raise RuntimeError("AIDetector is required when mode is 'detect'.")
            return self.detector.detect(frame)

        return self.frame_processor.process_frame(frame, self.mode)
