# video_frame_processor Design

## Scope
This document explains design intent, module boundaries, and extension strategy.
For setup and basic usage, see `README.md`.
For AI assistant working context, see `docs/ai_context.md`.

## Design Goals
- Keep the v1 pipeline simple and reliable
- Separate orchestration, I/O, processing logic, and utilities
- Make new processing modes easy to add without changing pipeline control flow
- Preserve one clear execution path for debugging and future expansion

## Architecture Overview
Core runtime flow:
1. Parse CLI arguments in `main.py`
2. Resolve input path and validate source file
3. Read frames through `VideoReader`
4. Process each frame through `FrameProcessor`
5. Display preview window (optional)
6. Write processed video to disk (optional)
7. Release all resources on normal exit or error

## Module Responsibilities
- `src/main.py`
  - Owns argument parsing and the main processing loop
  - Controls optional display and output writer lifecycle
  - Handles user-facing runtime errors and warnings
- `src/video_reader.py`
  - Wraps OpenCV `VideoCapture`
  - Provides frame reads plus FPS and frame size metadata
  - Encapsulates input backend details from the rest of the code
- `src/frame_processor.py`
  - Implements per-frame mode logic (`original`, `gray`, `edge`)
  - Normalizes output to BGR for consistent display and writer behavior
- `src/utils.py`
  - Resolves flexible input path patterns
  - Creates output directories and `VideoWriter`
  - Provides shared project path helpers

## Processing Pipeline Details
- Input path resolution supports:
  - absolute path
  - relative path
  - filename under project `input/`
- Display behavior:
  - disabled with `--no-display`
  - automatically disabled if `DISPLAY` is unavailable
- Output behavior:
  - enabled only when `--save` is provided
  - default path is `output/processed_output.mp4`

## Key Design Decisions
- Keep `main.py` as a thin orchestrator instead of placing image logic inline
  - Result: easier mode expansion and easier loop-level debugging
- Keep mode implementation in one processor module for v1
  - Result: small codebase remains understandable without early abstraction overhead
- Always return BGR frames from processing
  - Result: uniform downstream behavior for display and output writing
- Use fail-fast checks for invalid input path and unreadable video
  - Result: clearer error surfaces and lower debugging cost

## Future Extensions
- Promote mode functions to strategy classes when AI model modes are added
- Add additional input adapters (webcam, RTSP, stream)
- Introduce benchmark/test modules for throughput and correctness tracking
- Add optional acceleration backends behind stable processing interfaces
