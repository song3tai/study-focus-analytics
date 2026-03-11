# AI Context: video_frame_processor

## Project Summary
`video_frame_processor` is a v1 video processing project that reads video frames, applies one selected processing mode, optionally previews frames in a UI window, and can save processed output video.

## Current Status
- Core pipeline is implemented and runnable
- Current version is focused on engineering baseline, not model inference
- Code has been pushed to GitHub and is actively maintainable

## Current Features
- Frame-by-frame decoding via OpenCV
- Mode support:
  - `original`
  - `gray`
  - `edge`
- Optional display window for processed frames
- Optional output writing to `output/processed_output.mp4`
- Headless-safe execution with `--no-display` and `DISPLAY` fallback

## Project Structure (Core)
- `src/main.py`: CLI parsing and runtime orchestration
- `src/video_reader.py`: `VideoCapture` wrapper and metadata access
- `src/frame_processor.py`: mode-specific frame transformations
- `src/utils.py`: path resolution and writer/helper utilities
- `docs/design.md`: design rationale and architecture notes

## Tech Stack
- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy (`numpy`)

## Development Rules
- Keep module boundaries stable:
  - orchestration in `main.py`
  - I/O in `video_reader.py`
  - processing logic in `frame_processor.py`
- Keep `FrameProcessor` outputs in BGR format for pipeline consistency
- Add new processing modes without breaking existing CLI behavior
- Avoid adding setup/run instructions here; keep user-facing execution docs in `README.md`
- Update `docs/design.md` when architecture or design decisions change

## Roadmap / Next Steps
- Add a mode extension pattern for model-based processors
- Add test cases for mode correctness and path resolution
- Support additional input sources (webcam/RTSP)
- Introduce basic performance metrics collection

## Documentation Boundary
- `README.md`: quick project entry for humans (what/how to run)
- `docs/design.md`: architecture and decisions (why/how modules cooperate)
- `docs/ai_context.md` (this file): current implementation context for AI coding assistants
