# video_frame_processor Design (v1)

## Current Module Split
- `main.py`: command-line arguments, runtime loop, display, optional output saving.
- `video_reader.py`: video loading and frame/metadata access.
- `frame_processor.py`: image processing strategies (`original`, `gray`, `edge`).
- `utils.py`: shared path handling, output directory creation, writer creation.

## Why This Split
- Keeps I/O concerns (`video_reader`) separate from image logic (`frame_processor`).
- Keeps orchestration in one place (`main`) for easier maintenance.
- Keeps reusable helpers (`utils`) centralized and lightweight.

## Expansion Path Toward AI Video Analysis
- Add model-based processors in `frame_processor.py` or split into strategy modules.
- Add streaming input adapters (webcam/RTSP) by extending `video_reader.py`.
- Add async/batch and metrics helpers under `utils.py` or new modules.
- Add C++ acceleration integration behind the same processing interface to avoid changing main loop behavior.
