# Tests

This directory contains automated tests for pipeline behavior and mode correctness.

## Tooling
- `pytest`: test runner and assertions
- `numpy`: deterministic test frame generation
- Built-in mocking through `pytest`'s `monkeypatch` fixture and simple dummy classes

## Test Strategy
- Fast feedback first:
  - Use small synthetic frames instead of real videos
  - Avoid real model inference in unit tests
- Boundary-focused coverage:
  - Traditional processing modes (`original`, `gray`, `edge`)
  - Pipeline mode routing (`process` vs `detect`)
  - Required dependency checks (detect mode requires detector)
- Deterministic AI detector tests:
  - Stub `ultralytics.YOLO` to verify single-load behavior
  - Verify `detect()` returns annotated frame output

## Current Test Files
- `test_frame_processor.py`: validates core frame mode behavior
- `test_pipeline_modes.py`: validates pipeline flow and resource release
- `test_ai_detector.py`: validates detector lazy-loading and inference call path

## Run
```bash
cd /home/song3tai/phoenix/projects/ai_audio_video/video_frame_processor
source .venv/bin/activate
pytest -q
```
