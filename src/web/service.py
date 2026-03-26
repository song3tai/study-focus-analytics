"""Runtime service for the local analysis web boundary."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import threading
from time import perf_counter, sleep
from typing import Any

import cv2
import numpy as np

from src.app.analysis_runner import run_fast_analysis
from src.app.session_result_builder import finalize_session_result
from src.config import AppConfig
from src.core.enums import AnalysisMode, SourceType
from src.core.models import FramePacket, ProcessResult, SessionResult
from src.inference.ai_detector import AIDetector
from src.io.video_reader import FrameSource, create_frame_source
from src.pipeline import LocalAnalysisPipeline, PipelineConfig
from src.pipeline.analysis_pipeline import calculate_timestamp_seconds, render_analysis_preview
from src.utils import project_root, resolve_input_path
from src.web.websocket_manager import WebSocketManager


@dataclass(slots=True)
class AnalysisSessionStatus:
    running: bool
    session_state: str
    source_type: str | None
    source: str | None
    started_at: str | None
    has_latest_result: bool
    last_frame_id: int | None
    last_timestamp: float | None
    last_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "session_state": self.session_state,
            "source_type": self.source_type,
            "source": self.source,
            "started_at": self.started_at,
            "has_latest_result": self.has_latest_result,
            "last_frame_id": self.last_frame_id,
            "last_timestamp": self.last_timestamp,
            "last_error": self.last_error,
        }


class AnalysisWebService:
    """Manage one local analysis session for the FastAPI boundary."""

    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        websocket_manager: WebSocketManager | None = None,
    ) -> None:
        self.config = config or AppConfig()
        self.websocket_manager = websocket_manager or WebSocketManager()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session_state = "idle"
        self._running = False
        self._source_type: str | None = None
        self._source: str | None = None
        self._started_at: str | None = None
        self._last_error: str | None = None
        self._latest_result: ProcessResult | None = None
        self._latest_summary: dict[str, Any] | None = None
        self._latest_preview_jpeg: bytes | None = None
        self._active_reader: FrameSource | None = None
        self._active_pipeline: LocalAnalysisPipeline | None = None
        self._last_session_result: SessionResult | None = None

    def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start(
        self,
        *,
        source_type: str,
        source: str | None,
        debug: bool = False,
    ) -> tuple[bool, str]:
        with self._lock:
            if self._running or self._session_state in {"starting", "stopping"}:
                return False, "analysis session is already active"

            try:
                normalized_type, normalized_source = self._normalize_source(
                    source_type=source_type,
                    source=source,
                )
            except ValueError as exc:
                self._last_error = str(exc)
                self._session_state = "error"
                return False, str(exc)

            self._stop_event = threading.Event()
            self._running = True
            self._session_state = "starting"
            self._source_type = normalized_type
            self._source = normalized_source
            self._started_at = self._utc_now()
            self._last_error = None
            self._latest_result = None
            self._latest_summary = None
            self._latest_preview_jpeg = None
            self._active_pipeline = None
            self._last_session_result = None
            self._thread = threading.Thread(
                target=self._run_loop,
                kwargs={
                    "source_type": normalized_type,
                    "source": normalized_source,
                    "debug": debug,
                },
                daemon=True,
                name="analysis-web-service",
            )
            self._thread.start()

        self._publish_status("starting")
        return True, "analysis session starting"

    def stop(self) -> tuple[bool, str, SessionResult | None]:
        thread: threading.Thread | None = None
        with self._lock:
            if not self._running and self._session_state == "idle":
                return True, "analysis session is already stopped", None

            self._session_state = "stopping"
            self._stop_event.set()
            thread = self._thread
            active_reader = self._active_reader

        self._publish_status("stopping")
        if active_reader is not None:
            try:
                active_reader.release()
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                self._last_error = "analysis session did not stop cleanly"
                self._session_state = "error"
                self._running = False
                self._publish_error("analysis session did not stop cleanly")
                return False, "analysis session did not stop cleanly", None

            self._running = False
            self._thread = None
            self._session_state = "idle" if self._last_error is None else "error"
            self._latest_preview_jpeg = None
            session_result = self._last_session_result

        self._publish_status("stopped")
        return True, "analysis session stopped", session_result

    def shutdown(self) -> None:
        self.stop()

    def get_status(self) -> AnalysisSessionStatus:
        with self._lock:
            latest_result = self._latest_result
            return AnalysisSessionStatus(
                running=self._running,
                session_state=self._session_state,
                source_type=self._source_type,
                source=self._source,
                started_at=self._started_at,
                has_latest_result=latest_result is not None,
                last_frame_id=latest_result.frame_id if latest_result is not None else None,
                last_timestamp=latest_result.timestamp if latest_result is not None else None,
                last_error=self._last_error,
            )

    def get_status_payload(self) -> dict[str, Any]:
        return self.get_status().to_dict()

    def get_latest_result(self) -> ProcessResult | None:
        with self._lock:
            return self._latest_result

    def get_latest_summary(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._latest_summary) if self._latest_summary is not None else None

    def get_last_session_result(self) -> SessionResult | None:
        with self._lock:
            return self._last_session_result

    def run_analysis(self, *, source_type: str, source: str, mode: str) -> SessionResult:
        """Run a synchronous offline analysis request for one local file."""
        normalized_source_type = source_type.strip().lower()
        normalized_mode = mode.strip().lower()
        if normalized_source_type != "video_file":
            raise ValueError("only video_file is supported for /analysis/run")
        if normalized_mode != AnalysisMode.FAST.value:
            raise ValueError("only fast mode is supported for /analysis/run")
        return run_fast_analysis(source)

    def get_current_timestamp(self) -> str:
        return self._utc_now()

    def get_latest_preview_jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_preview_jpeg

    def preview_stream(self):
        """Yield an MJPEG stream for the latest rendered analysis preview."""
        while True:
            frame_bytes = self.get_latest_preview_jpeg() or self._build_placeholder_jpeg()
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            sleep(0.2)

    def _run_loop(self, *, source_type: str, source: str, debug: bool) -> None:
        reader: FrameSource | None = None
        pipeline: LocalAnalysisPipeline | None = None
        try:
            reader = self._create_frame_source(source_type=source_type, source=source)
            with self._lock:
                self._active_reader = reader
            detector = AIDetector(
                model_name=self.config.yolo_model_name,
                conf_threshold=self.config.yolo_conf_threshold,
            )
            width, height = reader.frame_size()
            roi = self.config.build_roi(width=width, height=height)
            pipeline = LocalAnalysisPipeline(
                roi=roi,
                config=PipelineConfig(enable_debug_logging=debug),
                analysis_mode=AnalysisMode.REALTIME,
            )
            pipeline.reset()

            with self._lock:
                self._active_pipeline = pipeline
                self._session_state = "running"

            self._publish_status("running")

            frame_index = 0
            source_fps = reader.fps()
            started_monotonic = perf_counter()
            while not self._stop_event.is_set():
                ok, frame = reader.read_frame()
                if not ok:
                    if self._attempt_live_reconnect(reader):
                        source_fps = reader.fps()
                        continue
                    break

                timestamp_seconds = calculate_timestamp_seconds(
                    frame_index=frame_index,
                    source_fps=source_fps,
                    is_live=reader.is_live,
                    started_monotonic=started_monotonic,
                )
                frame_packet = FramePacket(
                    frame_id=frame_index,
                    timestamp=timestamp_seconds,
                    source_type=self._to_source_enum(source_type),
                    source_name=getattr(reader, "source_label", source),
                    is_live=reader.is_live,
                    frame=frame,
                    fps_hint=source_fps,
                )
                detection_result = detector.detect_frame(
                    frame,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                )
                result = pipeline.process_frame(
                    frame_packet=frame_packet,
                    detection_result=detection_result,
                )
                preview_frame = render_analysis_preview(
                    result=result,
                    roi=roi,
                    detector=detector,
                    draw_roi=False,
                )
                with self._lock:
                    self._latest_result = result
                    self._latest_summary = result.summary.to_dict() if result.summary is not None else None
                    self._latest_preview_jpeg = self._encode_preview_frame(preview_frame)
                self._publish_result(result)
                frame_index += 1
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
                self._session_state = "error"
            self._publish_error(str(exc))
        finally:
            if pipeline is not None and pipeline.get_latest_result() is not None:
                session_result = finalize_session_result(pipeline)
                with self._lock:
                    self._last_session_result = session_result

            if reader is not None:
                reader.release()

            with self._lock:
                self._running = False
                self._thread = None
                self._active_reader = None
                self._active_pipeline = None
                self._latest_preview_jpeg = None
                if self._session_state != "error":
                    self._session_state = "idle"
            self._publish_status("idle" if self._last_error is None else "error")

    def _create_frame_source(self, *, source_type: str, source: str) -> FrameSource:
        input_path: Path | None = None
        use_camera = source_type == "camera"
        camera_index = self.config.default_camera_index
        rtsp_url: str | None = None

        if source_type == "video_file":
            input_path = resolve_input_path(source, project_root())
            if not input_path.exists() or not input_path.is_file():
                raise ValueError(f"video file not found: {input_path}")
        elif source_type == "camera":
            try:
                camera_index = int(source)
            except ValueError as exc:
                raise ValueError(f"invalid camera source: {source}") from exc
        elif source_type == "rtsp":
            rtsp_url = source
        else:
            raise ValueError(f"unsupported source type: {source_type}")

        return create_frame_source(
            input_path=input_path,
            use_camera=use_camera,
            camera_index=camera_index,
            rtsp_url=rtsp_url,
            rtsp_transport=self.config.default_rtsp_transport,
            fallback_fps=self.config.fallback_fps,
        )

    def _attempt_live_reconnect(self, reader: FrameSource) -> bool:
        if not reader.is_live:
            return False

        for attempt in range(1, self.config.live_reconnect_attempts + 1):
            if self._stop_event.is_set():
                return False
            if reader.reconnect():
                return True
            if attempt < self.config.live_reconnect_attempts:
                sleep(self.config.live_reconnect_interval_sec)
        return False

    def _normalize_source(self, *, source_type: str, source: str | None) -> tuple[str, str]:
        normalized_type = source_type.strip().lower()
        if normalized_type not in {"camera", "video_file", "rtsp"}:
            raise ValueError("source_type must be one of: camera, video_file, rtsp")

        if normalized_type == "camera":
            if source is None or str(source).strip() == "":
                return normalized_type, str(self.config.default_camera_index)
            return normalized_type, str(source).strip()

        if source is None or not str(source).strip():
            raise ValueError("source is required for video_file and rtsp sources")
        return normalized_type, str(source).strip()

    def _publish_result(self, result: ProcessResult) -> None:
        self._schedule_broadcast(
            {
                "type": "process_result",
                "timestamp": self._utc_now(),
                "data": result.to_dict(),
            }
        )

    def _publish_status(self, state_override: str | None = None) -> None:
        payload = self.get_status_payload()
        if state_override is not None:
            payload["session_state"] = state_override
        self._schedule_broadcast(
            {
                "type": "service_status",
                "timestamp": self._utc_now(),
                "data": payload,
            }
        )

    def _publish_error(self, message: str) -> None:
        self._schedule_broadcast(
            {
                "type": "service_error",
                "timestamp": self._utc_now(),
                "data": {
                    "message": message,
                    "session_state": "error",
                },
            }
        )

    def _schedule_broadcast(self, payload: dict[str, Any]) -> Future[Any] | None:
        if self._loop is None or self._loop.is_closed():
            return None
        return asyncio.run_coroutine_threadsafe(
            self.websocket_manager.broadcast_json(payload),
            self._loop,
        )

    @staticmethod
    def _to_source_enum(source_type: str) -> SourceType:
        if source_type == "camera":
            return SourceType.CAMERA
        if source_type == "rtsp":
            return SourceType.RTSP
        return SourceType.FILE

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _encode_preview_frame(frame: np.ndarray) -> bytes | None:
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not success:
            return None
        return encoded.tobytes()

    def _build_placeholder_jpeg(self) -> bytes:
        with self._lock:
            session_state = self._session_state
            source_type = self._source_type or "none"
            last_error = self._last_error

        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        frame[:] = (22, 28, 36)
        cv2.putText(frame, "Study Focus Analytics", (28, 64), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (235, 235, 235), 2, cv2.LINE_AA)
        cv2.putText(frame, f"session_state: {session_state}", (28, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (110, 210, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"source_type: {source_type}", (28, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (110, 210, 255), 2, cv2.LINE_AA)
        message = "waiting for analysis preview..."
        if session_state == "error" and last_error:
            message = f"error: {last_error}"
        elif session_state in {"starting", "running"}:
            message = "video preview not ready yet"
        cv2.putText(frame, message[:80], (28, 242), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        encoded = self._encode_preview_frame(frame)
        return encoded or b""
