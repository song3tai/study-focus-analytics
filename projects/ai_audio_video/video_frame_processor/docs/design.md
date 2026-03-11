# video_frame_processor Design

## Scope
This document explains the engineering structure of the upgraded pipeline-based prototype.
For installation and user-facing commands, see `README.md`.

## Design Goals
- Keep `main.py` thin and focused on startup concerns
- Separate input, processing, AI inference, output, and orchestration responsibilities
- Support both classic image processing and AI detection under one runtime flow
- Keep extension points clear for camera/stream input and backend replacement

## Architecture Overview
Current runtime pipeline:
1. `main.py` parses arguments and builds runtime modules
2. `VideoReader` opens video source and provides frames/metadata
3. `VideoPipeline` runs frame loop
4. Frame step:
   - Non-AI modes: `FrameProcessor.process_frame(...)`
   - AI mode: `AIDetector.detect(...)`
5. Optional display via OpenCV window
6. Optional save via `VideoWriter`
7. Resource cleanup on exit

## Module Responsibilities
- `src/main.py`
  - CLI parsing and argument validation
  - Component initialization
  - Pipeline startup
- `src/pipeline.py`
  - End-to-end frame loop orchestration
  - Mode dispatch (`process` vs `detect`)
  - Display/write flow control and cleanup
- `src/video_reader.py`
  - Video source abstraction based on OpenCV `VideoCapture`
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

## Key Design Decisions
- Introduced `pipeline.py` to prevent orchestration logic from accumulating in `main.py`
- Added dedicated `video_writer.py` to isolate OpenCV write concerns
- Added `ai_detector.py` for model lifecycle and inference isolation
- Kept classic processing and AI detection as parallel mode paths to avoid premature abstraction
- Added `config.py` because defaults now span CLI, output, and AI inference settings

## Processing Modes
- `original`: pass-through frames
- `gray`: grayscale conversion (returned as BGR)
- `edge`: Canny edges (returned as BGR)
- `detect`: YOLOv8 inference with box/label annotations

## Extension Path
- Input layer: add camera/RTSP/WebRTC reader adapters behind `VideoReader`-compatible interfaces
- AI layer: add multiple detector backends while preserving detector API shape
- Output layer: add structured JSON event output alongside video writing
- Performance layer: add batching, async pipelines, or native acceleration bridge (C++/TensorRT)
