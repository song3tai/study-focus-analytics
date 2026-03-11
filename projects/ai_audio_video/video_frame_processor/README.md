# video_frame_processor

## Project Overview
`video_frame_processor` is an AI video analysis prototype built with Python, OpenCV, and YOLOv8.
It supports frame-by-frame processing, real-time preview, optional output saving, and object detection annotation.

## Features
- Video frame decoding with OpenCV
- Processing modes:
  - `original`
  - `gray`
  - `edge`
  - `detect` (YOLOv8 object detection with bounding boxes and labels)
- Real-time UI playback
- Optional output video saving
- Headless-safe execution with `--no-display`

## Requirements
- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy (`numpy`)
- Ultralytics (`ultralytics`)

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
python src/main.py --input <video_file> --mode <original|gray|edge|detect> [--save] [--no-display]
```

## Example Commands
```bash
python src/main.py --input sample.mp4 --mode original
python src/main.py --input sample.mp4 --mode gray --save
python src/main.py --input sample.mp4 --mode edge --save
python src/main.py --input sample.mp4 --mode detect --model yolov8n.pt --conf 0.35
python src/main.py --input sample.mp4 --mode detect --save --no-display
```

## Notes
- `--input` supports absolute path, relative path, or filename under `input/`
- `--output <path>` can override default output file (`output/processed_output.mp4`)
- In `detect` mode, YOLO weights are loaded once and reused for all frames
- First YOLO run may download model weights

## Project Structure
- `src/main.py`: CLI entrypoint and module wiring
- `src/pipeline.py`: pipeline orchestration (`read -> process/detect -> display -> save`)
- `src/video_reader.py`: video input abstraction
- `src/frame_processor.py`: traditional frame processing modes
- `src/ai_detector.py`: YOLOv8 model loading and inference
- `src/video_writer.py`: output writer abstraction
- `src/config.py`: centralized defaults
- `src/utils.py`: common helper utilities

## Documentation
- Design details: `docs/design.md`
- AI assistant context: `docs/ai_context.md`

## Future Improvements
- Webcam and RTSP/WebRTC input adapters
- Structured JSON detection output
- Performance profiling and benchmarking
- C++ inference backend integration
