from __future__ import annotations

import numpy as np
import pytest

from config import AppConfig
from pipeline import VideoPipeline


class DummyReader:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = frames
        self._idx = 0
        self.released = False

    def read_frame(self):
        if self._idx >= len(self._frames):
            return False, None
        frame = self._frames[self._idx]
        self._idx += 1
        return True, frame

    def release(self) -> None:
        self.released = True


class DummyProcessor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def process_frame(self, frame: np.ndarray, mode: str) -> np.ndarray:
        self.calls.append(mode)
        return frame + 1


class DummyWriter:
    def __init__(self) -> None:
        self.frames_written = 0
        self.released = False

    def write_frame(self, frame: np.ndarray) -> None:
        self.frames_written += 1

    def release(self) -> None:
        self.released = True


class DummyDetector:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, frame: np.ndarray) -> np.ndarray:
        self.calls += 1
        return frame + 2


def _frames(n: int = 3) -> list[np.ndarray]:
    return [np.zeros((8, 8, 3), dtype=np.uint8) for _ in range(n)]


def test_pipeline_traditional_mode_uses_processor_and_writer() -> None:
    reader = DummyReader(_frames(3))
    processor = DummyProcessor()
    writer = DummyWriter()

    pipeline = VideoPipeline(
        reader=reader,
        frame_processor=processor,
        config=AppConfig(),
        mode="gray",
        display_enabled=False,
        writer=writer,
        detector=None,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert processor.calls == ["gray", "gray", "gray"]
    assert writer.frames_written == 3
    assert reader.released is True
    assert writer.released is True


def test_pipeline_detect_mode_uses_detector_not_processor() -> None:
    reader = DummyReader(_frames(2))
    processor = DummyProcessor()
    detector = DummyDetector()

    pipeline = VideoPipeline(
        reader=reader,
        frame_processor=processor,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=detector,
    )

    exit_code = pipeline.run()

    assert exit_code == 0
    assert detector.calls == 2
    assert processor.calls == []
    assert reader.released is True


def test_pipeline_detect_mode_requires_detector() -> None:
    reader = DummyReader(_frames(1))
    processor = DummyProcessor()

    pipeline = VideoPipeline(
        reader=reader,
        frame_processor=processor,
        config=AppConfig(),
        mode="detect",
        display_enabled=False,
        writer=None,
        detector=None,
    )

    with pytest.raises(RuntimeError, match="AIDetector is required"):
        pipeline.run()

    assert reader.released is True
