from __future__ import annotations

import numpy as np
import pytest

from frame_processor import FrameProcessor


@pytest.fixture
def sample_frame() -> np.ndarray:
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    frame[4:12, 4:12] = [255, 255, 255]
    return frame


def test_original_mode_returns_input_frame(sample_frame: np.ndarray) -> None:
    processor = FrameProcessor()
    result = processor.process_frame(sample_frame, "original")
    assert np.array_equal(result, sample_frame)


def test_gray_mode_returns_bgr_shape(sample_frame: np.ndarray) -> None:
    processor = FrameProcessor()
    result = processor.process_frame(sample_frame, "gray")
    assert result.shape == sample_frame.shape
    assert result.dtype == sample_frame.dtype


def test_edge_mode_returns_bgr_shape(sample_frame: np.ndarray) -> None:
    processor = FrameProcessor()
    result = processor.process_frame(sample_frame, "edge")
    assert result.shape == sample_frame.shape
    assert result.dtype == sample_frame.dtype


def test_unsupported_mode_raises_value_error(sample_frame: np.ndarray) -> None:
    processor = FrameProcessor()
    with pytest.raises(ValueError):
        processor.process_frame(sample_frame, "unknown")
