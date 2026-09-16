from __future__ import annotations

import logging
import os
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.broker.access_adapter import BrokerAccessAdapter
from app.core.config import settings
from app.routes.health import make_health
from app.routes.workspace import router as workspace_router
from app.providers.deepseek_provider import DeepSeekProvider
from app.services.ai_service import AIService
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.chart_service import ChartService
from app.services.file_service import FileService
from app.services.report_service import ReportService
from app.services.workspace_service import WorkspaceService


logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title=settings.app_name, docs_url=None, redoc_url=None, root_path=os.getenv("ROOT_PATH", ""))
workspace = WorkspaceService(settings); files = FileService(settings); artifacts = ArtifactService(settings); broker = BrokerAccessAdapter(settings)
app.state.workspace = workspace
app.state.services = SimpleNamespace(settings=settings, workspace=workspace, files=files, artifacts=artifacts,
                                     analysis=AnalysisService(settings), charts=ChartService(), reports=ReportService(),
                                     broker=broker, broker_ready=False, ai=AIService(DeepSeekProvider(broker)))
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(workspace_router)
app.include_router(make_health(app))


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Keep browser-side data handling constrained even outside the proxy."""
    response = await call_next(request)
    if os.getenv("APP_SECURITY_HEADERS", "true").lower() != "true":
        return response
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "img-src 'self' data:; style-src 'self'; object-src 'none'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.on_event("startup")
async def startup() -> None:
    workspace.initialize(); files.initialize(); artifacts.initialize()
    try:
        await app.state.services.broker.validate()
        app.state.services.broker_ready = True
    except Exception as exc:
        logging.getLogger(__name__).warning("broker_unavailable_at_startup", extra={"event": "broker_error", "reason": type(exc).__name__})
    logging.getLogger(__name__).info("workspace_started", extra={"event": "startup"})


@app.on_event("shutdown")
async def shutdown() -> None:
    logging.getLogger(__name__).info("workspace_stopped", extra={"event": "shutdown"})
