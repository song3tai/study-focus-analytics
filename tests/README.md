# Tests

This directory contains automated tests for the V1 analysis pipeline and its supporting modules.

## Tooling
- `pytest`: test runner and assertions
- `numpy`: deterministic test frame generation
- `opencv-python`: provides `cv2` for IO / pipeline module imports
- Built-in mocking through `pytest`'s `monkeypatch` fixture and simple dummy classes

## Test Strategy
- Fast feedback first:
  - Use small synthetic frames instead of real videos
  - Avoid real model inference in unit tests
- Boundary-focused coverage:
  - Pipeline mode routing (`analyze` vs `detect`)
  - Required dependency checks (detect mode requires detector)
  - State transitions, focus estimation, and summary aggregation
- Deterministic AI detector tests:
  - Stub `ultralytics.YOLO` to verify single-load behavior
  - Verify structured detection output is stable

## Current Test Files
- `test_pipeline_modes.py`: validates pipeline flow and resource release
- `test_ai_detector.py`: validates detector lazy-loading and inference call path
- `test_behavior_modules.py`: validates scene features, state tracking, focus, and summary logic

## Run
```bash
cd /home/song3tai/study-focus-analytics
source .venv/bin/activate
python3 -m pytest -q
```

If test collection fails with `ModuleNotFoundError: No module named 'cv2'`, install dependencies from `requirements.txt` first.
