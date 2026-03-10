# video_frame_processor

## Project Overview
`video_frame_processor` is an engineering-focused project for frame-by-frame video reading and basic image processing.

This repository is the first stage of a larger AI video analysis roadmap.  
The current goal is to build a clean, testable processing pipeline before adding model-based features.

This README is maintained as the primary project context document.  
When code behavior, structure, environment requirements, or usage changes, the README should be updated accordingly so it can be reused as reliable context for future development and for external AI tools.

## Features
- Frame-by-frame video decoding with OpenCV
- Processing modes:
  - `original` (raw frame)
  - `gray` (grayscale)
  - `edge` (Canny edge detection)
- Real-time visualization in a desktop window
- Optional headless execution via `--no-display`
- Automatic fallback to non-display mode when `DISPLAY` is unavailable
- Optional processed video export to `output/processed_output.mp4`
- Safe runtime behavior: input validation, clear errors, and resource cleanup
- Flexible input resolution:
  - absolute file path
  - relative file path
  - filename located under `input/`

## Project Structure
- `src/main.py`: argument parsing, runtime loop, display/write orchestration
- `src/video_reader.py`: video open/read/metadata abstraction
- `src/frame_processor.py`: frame transformation logic by mode
- `src/utils.py`: shared helpers for path handling and video writer setup
- `src/__pycache__/`: Python bytecode cache generated locally at runtime
- `input/`: local input videos
- `output/`: generated output videos
- `docs/`: design notes
- `scripts/`: helper scripts (reserved)
- `tests/`: test extension area (reserved)

## Requirements
- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy (`numpy`)

## Environment Setup (WSL + venv Recommended)
Install Python runtime components (one-time, system level):

```bash
sudo apt-get update && sudo apt-get install -y python3.10-venv python3-pip
```

Create and initialize the project virtual environment:

```bash
cd /home/song3tai/phoenix/projects/ai_audio_video/video_frame_processor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## Usage
Run from project root:

```bash
python src/main.py --input <video_file> --mode <original|gray|edge> [--save] [--no-display]
```

Notes:
- `--input` accepts an absolute path, relative path, or a filename placed in `input/`.
- Press `ESC` to exit early.
- `--save` writes processed output to `output/processed_output.mp4`.
- `--no-display` disables the preview window and is recommended in WSL/headless environments.
- If `DISPLAY` is not set, the program automatically disables preview and continues running.

## Example Commands
```bash
python src/main.py --input input/sample.mp4 --mode original
python src/main.py --input sample.mp4 --mode gray
python src/main.py --input sample.mp4 --mode edge --save
python src/main.py --input sample.mp4 --mode gray --no-display
```

## Daily Start / Exit Commands
Start working session:

```bash
cd /home/song3tai/phoenix/projects/ai_audio_video/video_frame_processor
source .venv/bin/activate
```

Run project:

```bash
python src/main.py --input input/sample.mp4 --mode gray
```

Exit virtual environment:

```bash
deactivate
```

## Future Conda Migration (Smooth Switch)
If dependencies become heavier (for example, GPU frameworks), you can switch to conda while keeping `requirements.txt`:

```bash
conda create -n video-frame-processor python=3.10 -y
conda activate video-frame-processor
python -m pip install -r requirements.txt
```

## Troubleshooting
If OpenCV preview fails in WSL with a Qt/xcb error such as `Could not load the Qt platform plugin "xcb"`, install the required system libraries:

```bash
sudo apt-get update
sudo apt-get install -y libsm6 libice6 libxext6 libxrender1 libglib2.0-0
```

If you only need to verify processing and output generation, run without preview:

```bash
python src/main.py --input input/sample.mp4 --mode gray --no-display --save
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
