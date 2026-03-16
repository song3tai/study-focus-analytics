# video_frame_processor

## Project Overview
`video_frame_processor` is an AI video analysis prototype built with Python, OpenCV, and YOLOv8.
It supports frame-by-frame processing, real-time preview, optional output saving for video files, and real-time object detection annotation for video files and live RTSP streams.

## Features
- Video frame decoding with OpenCV
- Real-time RTSP stream capture with OpenCV
- Processing modes:
  - `original`
  - `gray`
  - `edge`
  - `detect` (YOLOv8 object detection with bounding boxes and labels)
- Real-time UI playback
- FPS overlay in preview frames
- Optional output video saving for file input
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
python3 src/main.py --input <video_file> --mode <original|gray|edge|detect> [--save] [--no-display]
python3 src/main.py --rtsp-url --mode detect
python3 src/main.py --rtsp-url <rtsp_url> --rtsp-transport auto --mode detect
```

## Example Commands
```bash
python3 src/main.py --rtsp-url --mode detect
python3 src/main.py --input sample.mp4 --mode original
python3 src/main.py --input sample.mp4 --mode gray --save
python3 src/main.py --input sample.mp4 --mode edge --save
python3 src/main.py --input sample.mp4 --mode detect --model yolov8n.pt --conf 0.35
python3 src/main.py --input sample.mp4 --mode detect --save --no-display
python3 src/main.py --rtsp-url rtsp://172.29.160.1:8554/live --rtsp-transport udp --mode detect
python3 src/main.py --rtsp-url rtsp://192.168.3.3:8554/live --rtsp-transport auto --mode detect
python3 src/main.py --rtsp-url rtsp://192.168.3.3:8554/live --mode original
```

## Input Modes
- Video file mode:
  - Start with `--input <path>`
  - Supports `original`, `gray`, `edge`, `detect`
  - Supports `--save`
- RTSP stream mode:
  - Start with `--rtsp-url <url>`
  - `--rtsp-url` without a value uses the current default stream URL
  - `--rtsp-transport` supports `auto|tcp|udp`, default is `auto`
  - Intended for real-time preview and YOLO detection
  - Current default stream in this environment: `rtsp://192.168.3.3:8554/live`
  - Current stage does not support `--save`

## Real-Time RTSP Detection
```bash
python3 src/main.py --rtsp-url --mode detect
python3 src/main.py --rtsp-url rtsp://172.29.160.1:8554/live --rtsp-transport udp --mode detect
```

Behavior:
- Opens the specified RTSP stream
- In `auto` mode, tries `tcp` first and falls back to `udp`
- Runs YOLOv8 inference on each frame
- Displays annotated boxes and class labels
- Shows FPS in the top-left corner
- Exits cleanly on `ESC`
- Retries live stream reconnect on transient frame-read failures

## Notes
- `--input` supports absolute path, relative path, or filename under `input/`
- `--rtsp-url` is intended for live network streams such as VLC-published webcam feeds
- VLC-published RTSP streams may require `--rtsp-transport udp`
- Default `--rtsp-transport auto` will try `tcp` first and then `udp`
- `--output <path>` overrides the default output file (`output/processed_output.mp4`) for file mode
- In `detect` mode, YOLO weights are loaded once and reused for all frames
- RTSP open failures return a clear runtime error message
- First YOLO run may download model weights
- Live RTSP/camera output saving is intentionally disabled in this iteration to keep the live path simple and stable

## Project Structure
- `src/main.py`: CLI entrypoint and module wiring
- `src/pipeline.py`: pipeline orchestration (`read -> process/detect -> display -> optional save`)
- `src/video_reader.py`: file/live-stream input abstraction
- `src/frame_processor.py`: traditional frame processing modes
- `src/ai_detector.py`: YOLOv8 model loading and inference
- `src/video_writer.py`: output writer abstraction
- `src/config.py`: centralized defaults
- `src/utils.py`: common helper utilities

## Documentation
- Design details: `docs/design.md`
- AI assistant context: `docs/ai_context.md`

## Future Improvements
- WebRTC input adapters
- Structured JSON detection output
- Performance profiling and benchmarking
- C++ inference backend integration
