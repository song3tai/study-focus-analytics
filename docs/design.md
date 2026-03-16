# video_frame_processor Design

## Scope
This document explains the engineering structure of the upgraded pipeline-based prototype.
For installation and user-facing commands, see `README.md`.

## Design Goals
- Keep `main.py` thin and focused on startup concerns
- Separate input, processing, AI inference, output, and orchestration responsibilities
- Support both classic image processing and AI detection under one runtime flow
- Support both video files and live streams behind one input abstraction
- Keep extension points clear for camera/stream input and backend replacement

## Architecture Overview
Current runtime pipeline:
1. `main.py` parses arguments and builds runtime modules
2. Input source factory selects `VideoReader`, `RTSPReader`, or other future live readers
3. `VideoPipeline` runs frame loop
4. Frame step:
   - Non-AI modes: `FrameProcessor.process_frame(...)`
   - AI mode: `AIDetector.detect(...)`
5. `FPSCounter` updates per-frame FPS and overlays it on the frame
6. Optional display via OpenCV window
7. Live sources attempt bounded reconnect on transient read failures
8. Optional save via `VideoWriter` for file mode
9. Resource cleanup on exit

Pipeline shape:

Input Source (Video / RTSP)
↓
Frame Reader
↓
Frame Processor
↓
AI Detector
↓
Display
↓
Optional Save

## Module Responsibilities
- `src/main.py`
  - CLI parsing and argument validation
  - Input source selection (`--input` vs `--rtsp-url`)
  - Component initialization
  - Pipeline startup
- `src/pipeline.py`
  - End-to-end frame loop orchestration
  - Mode dispatch (`process` vs `detect`)
  - FPS calculation and frame overlay
  - Live source reconnect control
  - Display/write flow control and cleanup
- `src/video_reader.py`
  - `FrameSource` interface for reusable capture inputs
  - File source implementation (`VideoReader`)
  - RTSP source implementation (`RTSPReader`)
  - RTSP transport fallback and reconnect open logic
  - Frame reads and source metadata (`fps`, frame size)
- `src/frame_processor.py`
  - Traditional processing modes (`original`, `gray`, `edge`)
  - BGR output normalization
- `src/ai_detector.py`
  - YOLOv8 integration
  - Model lazy-loading and single-load reuse
  - Detection inference and annotation rendering
- `src/video_writer.py`
  - Output writer setup and frame persistence
  - Writer lifecycle encapsulation
- `src/config.py`
  - Centralized default runtime values
- `src/utils.py`
  - Shared generic helpers (project root, input resolution, directory creation)
  - FPS tracking and overlay helper

## Key Design Decisions
- Introduced `pipeline.py` to prevent orchestration logic from accumulating in `main.py`
- Added dedicated `video_writer.py` to isolate OpenCV write concerns
- Added `ai_detector.py` for model lifecycle and inference isolation
- Expanded `video_reader.py` into a small input layer instead of creating a larger stream subsystem
- Kept classic processing and AI detection as parallel mode paths to avoid premature abstraction
- Added `config.py` because defaults now span CLI, output, and AI inference settings
- Deferred live stream output saving to keep the first streaming pipeline reliable and easier to maintain
- Kept reconnect policy in `pipeline.py` and reconnect mechanics in `video_reader.py` to preserve clear ownership

## Processing Modes
- `original`: pass-through frames
- `gray`: grayscale conversion (returned as BGR)
- `edge`: Canny edges (returned as BGR)
- `detect`: YOLOv8 inference with box/label annotations

## Supported Inputs
- `video file`
  - Finite source
  - Supports display and optional save
- `rtsp stream`
  - Live source
  - Supports real-time display and detection
  - Supports configurable transport (`auto|tcp|udp`)
  - Supports bounded reconnect attempts on frame-read failure
  - Current stage does not persist output video

## Extension Path
- Input layer: add WebRTC or other live reader adapters behind the `FrameSource` interface
- AI layer: add multiple detector backends while preserving detector API shape
- Output layer: add structured JSON event output alongside video writing
- Performance layer: add batching, async pipelines, or native acceleration bridge (C++/TensorRT)
