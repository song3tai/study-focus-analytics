# video_frame_processor

## Project Overview
`video_frame_processor` is a Python/OpenCV project for frame-by-frame video processing.
It currently supports three processing modes (`original`, `gray`, `edge`), real-time preview, and optional processed video export.

## Features
- Frame-by-frame video decoding with OpenCV
- Processing modes:
  - `original` (raw frame)
  - `gray` (grayscale)
  - `edge` (Canny edge detection)
- Real-time UI window playback
- Optional output saving to `output/processed_output.mp4`
- Headless execution with `--no-display` (auto-disabled preview when `DISPLAY` is unavailable)
- Safe runtime behavior: input validation and resource cleanup

## Project Structure
- `src/main.py`: CLI entrypoint and runtime orchestration
- `src/video_reader.py`: video I/O and metadata access
- `src/frame_processor.py`: frame transformation by mode
- `src/utils.py`: path and writer helper utilities
- `input/`: input videos
- `output/`: generated output videos
- `docs/design.md`: architecture and design decisions
- `docs/ai_context.md`: AI-focused project context

## Requirements
- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy (`numpy`)

## Installation
```bash
cd /home/song3tai/phoenix/projects/ai_audio_video/video_frame_processor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## Usage
```bash
python src/main.py --input <video_file> --mode <original|gray|edge> [--save] [--no-display]
```

Quick notes:
- `--input` supports absolute path, relative path, or filename under `input/`
- Press `ESC` to stop early when preview is enabled
- Use `--no-display` in headless/WSL environments

## Example Commands
```bash
python src/main.py --input input/sample.mp4 --mode original
python src/main.py --input sample.mp4 --mode gray
python src/main.py --input sample.mp4 --mode edge --save
python src/main.py --input sample.mp4 --mode gray --no-display --save
```

## Documentation
- Design and architecture: `docs/design.md`
- AI coding context and development constraints: `docs/ai_context.md`

## Future Improvements
- Add model-based processors (detection/tracking/classification)
- Add webcam/stream input adapters
- Improve testing coverage and benchmark visibility
