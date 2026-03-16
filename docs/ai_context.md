# AI Context: video_frame_processor

## Project Summary
This project has been upgraded from a simple frame-processing demo to a real-time AI detection prototype with a modular pipeline architecture oriented toward live stream processing.

## Current Status
- Pipeline architecture is active (`main -> pipeline -> modules`)
- YOLOv8 detection mode is integrated
- RTSP stream input is integrated for real-time detection
- RTSP transport fallback and reconnect support are integrated
- Existing classic modes remain supported (`original`, `gray`, `edge`)
- App supports preview, headless run, FPS overlay, and optional output writing for file input

## Current Features
- Video frame reading from file input
- Real-time frame reading from RTSP input
- Mode-based processing:
  - `original`
  - `gray`
  - `edge`
  - `detect` (YOLOv8 object detection)
- Annotated object boxes/labels in detect mode
- Real-time FPS overlay on displayed frames
- Automatic RTSP transport fallback (`auto -> tcp/udp`)
- Bounded reconnect attempts for live RTSP frame-read failures
- Optional save to output video for file input
- Headless-safe execution (`--no-display`)
- Clean shutdown on `ESC` during preview

## Project Structure (Core)
- `src/main.py`: parse args, initialize dependencies, start pipeline
- `src/pipeline.py`: run frame loop and route mode behavior
- `src/video_reader.py`: file/live-stream source frame reading, RTSP transport handling, and reconnect open logic
- `src/frame_processor.py`: non-AI processing logic
- `src/ai_detector.py`: AI model loading and inference
- `src/video_writer.py`: output writing abstraction
- `src/config.py`: default runtime configuration
- `src/utils.py`: shared helper utilities and FPS overlay support

## Tech Stack
- Python 3.10+
- OpenCV
- NumPy
- Ultralytics YOLOv8

## Development Rules
- Keep `main.py` lightweight; business runtime flow belongs in `pipeline.py`
- Keep model initialization inside `AIDetector`; never reload model per frame
- Preserve BGR frame outputs for display/write compatibility
- Keep new input types aligned to the `FrameSource` interface
- Keep transport negotiation and reopen logic inside source adapters, not inside `main.py`
- Extend functionality by adding modules, not by inflating one file
- Keep README user-focused; place architecture rationale in `docs/design.md`

## Roadmap / Next Steps
- Add WebRTC input support
- Add structured JSON detection output
- Add tests for pipeline mode behavior and detector failure handling
- Add optional high-performance inference backend integration

## Documentation Boundary
- `README.md`: user entry and run commands
- `docs/design.md`: design rationale and architecture
- `docs/ai_context.md`: implementation context for AI coding assistants
