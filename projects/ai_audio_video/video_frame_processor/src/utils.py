"""Utility helpers for video pipeline."""

from __future__ import annotations

from pathlib import Path

import cv2


def project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).resolve().parent.parent


def resolve_input_path(input_value: str, root: Path) -> Path:
    """Resolve input path from common user inputs.

    Supports:
    - absolute path
    - relative path from current working directory
    - filename under project input/ directory
    """
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


def create_video_writer(
    output_path: Path, width: int, height: int, fps: float
) -> cv2.VideoWriter:
    """Create a VideoWriter for mp4 output."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create output video writer: {output_path}")
    return writer


def default_output_path(root: Path) -> Path:
    """Return default output video path."""
    return root / "output" / "processed_output.mp4"
