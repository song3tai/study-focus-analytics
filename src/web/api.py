"""FastAPI app exposing current analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.core.models import ProcessResult
from src.web.schemas import ProcessResultResponse, SummaryResponse
from src.web.websocket_manager import WebSocketManager


@dataclass
class AnalysisStore:
    """In-memory store shared by REST and WebSocket endpoints."""

    latest_result: ProcessResult | None = None
    recent_events: list[dict] = field(default_factory=list)

    def update(self, result: ProcessResult, recent_events: list[dict]) -> None:
        self.latest_result = result
        self.recent_events = recent_events


def create_app(store: AnalysisStore | None = None) -> FastAPI:
    """Create the V1 API app."""
    app = FastAPI(title="Study Focus Analytics API", version="1.0.0")
    manager = WebSocketManager()
    analysis_store = store or AnalysisStore()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/current", response_model=ProcessResultResponse | None)
    async def get_current() -> ProcessResultResponse | None:
        if analysis_store.latest_result is None:
            return None
        return ProcessResultResponse.from_result(analysis_store.latest_result)

    @app.get("/api/summary", response_model=SummaryResponse | None)
    async def get_summary() -> SummaryResponse | None:
        if analysis_store.latest_result is None:
            return None
        return SummaryResponse.from_summary(analysis_store.latest_result.summary)

    @app.get("/api/events")
    async def get_events() -> list[dict]:
        return analysis_store.recent_events

    @app.websocket("/ws/analysis")
    async def analysis_socket(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
                if analysis_store.latest_result is not None:
                    await websocket.send_json(ProcessResultResponse.from_result(analysis_store.latest_result).model_dump())
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    app.state.analysis_store = analysis_store
    app.state.websocket_manager = manager
    return app
