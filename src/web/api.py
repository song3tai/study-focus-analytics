"""FastAPI app exposing the local analysis web boundary."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from src.web.schemas import (
    AnalysisStatusResponse,
    HealthResponse,
    LatestResultResponse,
    SimpleMessageResponse,
    StartAnalysisRequest,
    SummaryEnvelopeResponse,
)
from src.web.service import AnalysisWebService
from src.web.websocket_manager import WebSocketManager


APP_NAME = "Study Focus Analytics API"
API_VERSION = "1.0.0"


def create_app(service: AnalysisWebService | None = None) -> FastAPI:
    """Create the formal FastAPI application."""
    websocket_manager = WebSocketManager()
    analysis_service = service or AnalysisWebService(websocket_manager=websocket_manager)
    app = FastAPI(title=APP_NAME, version=API_VERSION)

    @app.on_event("startup")
    async def on_startup() -> None:
        analysis_service.bind_event_loop(asyncio.get_running_loop())

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        analysis_service.shutdown()

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app_name=APP_NAME,
            api_version=API_VERSION,
        )

    @app.get("/analysis/status", response_model=AnalysisStatusResponse)
    async def get_status() -> AnalysisStatusResponse:
        return AnalysisStatusResponse.from_status_payload(analysis_service.get_status_payload())

    @app.post("/analysis/start", response_model=SimpleMessageResponse)
    async def start_analysis(request: StartAnalysisRequest) -> SimpleMessageResponse | JSONResponse:
        success, message = analysis_service.start(
            source_type=request.source_type,
            source=request.source,
            debug=request.debug,
        )
        response = SimpleMessageResponse(
            success=success,
            message=message,
            session_state=analysis_service.get_status_payload()["session_state"],
        )
        if success:
            return response

        status_code = 409 if "already active" in message else 400
        return JSONResponse(status_code=status_code, content=response.model_dump())

    @app.post("/analysis/stop", response_model=SimpleMessageResponse)
    async def stop_analysis() -> SimpleMessageResponse:
        success, message = analysis_service.stop()
        return SimpleMessageResponse(
            success=success,
            message=message,
            session_state=analysis_service.get_status_payload()["session_state"],
        )

    @app.get("/analysis/latest", response_model=LatestResultResponse)
    async def get_latest() -> LatestResultResponse:
        latest_result = analysis_service.get_latest_result()
        if latest_result is None:
            return LatestResultResponse(
                has_result=False,
                data=None,
                message="no analysis result available yet",
            )
        return LatestResultResponse(
            has_result=True,
            data=latest_result.to_dict(),
            message="latest analysis result available",
        )

    @app.get("/analysis/summary", response_model=SummaryEnvelopeResponse)
    async def get_summary() -> SummaryEnvelopeResponse:
        latest_summary = analysis_service.get_latest_summary()
        if latest_summary is None:
            return SummaryEnvelopeResponse(
                has_summary=False,
                data=None,
                message="no summary available yet",
            )
        return SummaryEnvelopeResponse(
            has_summary=True,
            data=latest_summary,
            message="latest summary available",
        )

    @app.websocket("/ws/analysis")
    async def analysis_socket(websocket: WebSocket) -> None:
        await analysis_service.websocket_manager.connect(websocket)
        try:
            await analysis_service.websocket_manager.send_json(
                websocket,
                {
                    "type": "service_status",
                    "timestamp": analysis_service.get_current_timestamp(),
                    "data": analysis_service.get_status_payload(),
                },
            )
            latest_result = analysis_service.get_latest_result()
            if latest_result is not None:
                await analysis_service.websocket_manager.send_json(
                    websocket,
                    {
                        "type": "process_result",
                        "timestamp": analysis_service.get_current_timestamp(),
                        "data": latest_result.to_dict(),
                    },
                )
            await analysis_service.websocket_manager.wait_for_disconnect(websocket)
        except WebSocketDisconnect:
            pass
        finally:
            analysis_service.websocket_manager.disconnect(websocket)

    app.state.analysis_service = analysis_service
    return app


app = create_app()
