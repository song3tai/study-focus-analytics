"""Generic utility helpers."""

from __future__ import annotations

from pathlib import Path


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
