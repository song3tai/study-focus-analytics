"""Generic utility helpers."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import cv2
import numpy as np


def project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).resolve().parent.parent


def resolve_input_path(input_value: str, root: Path) -> Path:
    """Resolve input path from common user inputs."""
    raw = Path(input_value).expanduser()
    candidates: list[Path] = [raw]

    if not raw.is_absolute():
        candidates.append(root / raw)
        candidates.append(root / "input" / raw.name)

    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve(strict=False)
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized.exists():
            return normalized

    return raw.resolve(strict=False)


def ensure_dir(path: Path) -> None:
    """Create directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


class FPSCounter:
    """Track smoothed FPS for live display."""

    def __init__(self) -> None:
        self._last_tick: float | None = None
        self._fps: float = 0.0

    def tick(self) -> float:
        now = perf_counter()
        if self._last_tick is not None:
            elapsed = now - self._last_tick
            if elapsed > 0:
                instant_fps = 1.0 / elapsed
                self._fps = instant_fps if self._fps == 0.0 else (self._fps * 0.8) + (instant_fps * 0.2)
        self._last_tick = now
        return self._fps


def annotate_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    """Draw FPS text on frame in-place and return the same frame."""
    label = f"FPS: {fps:.2f}" if fps > 0 else "FPS: --"
    cv2.putText(
        frame,
        label,
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return frame
