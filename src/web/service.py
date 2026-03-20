"""Runtime service for the local analysis web boundary."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import threading
from time import sleep
from typing import Any

from src.config import AppConfig
from src.core.enums import SourceType
from src.core.models import FramePacket, ProcessResult
from src.inference.ai_detector import AIDetector
from src.io.video_reader import FrameSource, create_frame_source
from src.pipeline import LocalAnalysisPipeline, PipelineConfig
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

    def stop(self) -> tuple[bool, str]:
        thread: threading.Thread | None = None
        with self._lock:
            if not self._running and self._session_state == "idle":
                return True, "analysis session is already stopped"

            self._session_state = "stopping"
            self._stop_event.set()
            thread = self._thread

        self._publish_status("stopping")
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                self._last_error = "analysis session did not stop cleanly"
                self._session_state = "error"
                self._running = False
                self._publish_error("analysis session did not stop cleanly")
                return False, "analysis session did not stop cleanly"

            self._running = False
            self._thread = None
            self._session_state = "idle" if self._last_error is None else "error"

        self._publish_status("stopped")
        return True, "analysis session stopped"

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

    def get_current_timestamp(self) -> str:
        return self._utc_now()

    def _run_loop(self, *, source_type: str, source: str, debug: bool) -> None:
        reader: FrameSource | None = None
        try:
            reader = self._create_frame_source(source_type=source_type, source=source)
            detector = AIDetector(
                model_name=self.config.yolo_model_name,
                conf_threshold=self.config.yolo_conf_threshold,
            )
            width, height = reader.frame_size()
            roi = self.config.build_roi(width=width, height=height)
            pipeline = LocalAnalysisPipeline(
                roi=roi,
                config=PipelineConfig(enable_debug_logging=debug),
            )

            with self._lock:
                self._session_state = "running"

            self._publish_status("running")

            frame_index = 0
            source_fps = reader.fps()
            while not self._stop_event.is_set():
                ok, frame = reader.read_frame()
                if not ok:
                    if self._attempt_live_reconnect(reader):
                        source_fps = reader.fps()
                        continue
                    break

                timestamp_seconds = frame_index / max(source_fps, 1e-6)
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
                with self._lock:
                    self._latest_result = result
                    self._latest_summary = result.summary.to_dict() if result.summary is not None else None
                self._publish_result(result)
                frame_index += 1
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
                self._session_state = "error"
            self._publish_error(str(exc))
        finally:
            if reader is not None:
                reader.release()

            with self._lock:
                self._running = False
                self._thread = None
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
