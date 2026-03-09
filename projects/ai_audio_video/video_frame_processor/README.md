# video_frame_processor

## Project Overview
`video_frame_processor` is an engineering-focused project for frame-by-frame video reading and basic image processing.

This repository is the first stage of a larger AI video analysis roadmap.  
The current goal is to build a clean, testable processing pipeline before adding model-based features.

## Features
- Frame-by-frame video decoding with OpenCV
- Processing modes:
  - `original` (raw frame)
  - `gray` (grayscale)
  - `edge` (Canny edge detection)
- Real-time visualization in a desktop window
- Optional processed video export to `output/processed_output.mp4`
- Safe runtime behavior: input validation, clear errors, and resource cleanup

## Project Structure
- `src/main.py`: argument parsing, runtime loop, display/write orchestration
- `src/video_reader.py`: video open/read/metadata abstraction
- `src/frame_processor.py`: frame transformation logic by mode
- `src/utils.py`: shared helpers for path handling and video writer setup
- `input/`: local input videos
- `output/`: generated output videos
- `docs/`: design notes
- `scripts/`: helper scripts (reserved)
- `tests/`: test extension area (reserved)

## Requirements
- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy (`numpy`)

## Installation
```bash
cd /home/song3tai/phoenix/projects/ai_audio_video/video_frame_processor
pip install -r requirements.txt
```

## Usage
Run from project root:

```bash
python src/main.py --input <video_file> --mode <original|gray|edge> [--save]
```

Notes:
- `--input` accepts an absolute path, relative path, or a filename placed in `input/`.
- Press `ESC` to exit early.
- `--save` writes processed output to `output/processed_output.mp4`.

## Example Commands
```bash
python src/main.py --input input/sample.mp4 --mode original
python src/main.py --input sample.mp4 --mode gray
python src/main.py --input sample.mp4 --mode edge --save
```

## Design Notes
- `main.py` handles orchestration only, so control flow stays explicit and easy to maintain.
- `video_reader.py` isolates video I/O and metadata retrieval, preventing OpenCV details from leaking into business logic.
- `frame_processor.py` centralizes frame transformation rules, making new processing modes straightforward to add.
- `utils.py` holds reusable utility logic (path resolution, output creation), reducing duplication.

This separation keeps responsibilities clear and makes the codebase easier to extend with AI models, streaming inputs, and service integration.

## Future Improvements
- Object detection
- Face detection
- Video summarization
- Real-time streaming integration
- Model inference service
- C++ high-performance inference integration
