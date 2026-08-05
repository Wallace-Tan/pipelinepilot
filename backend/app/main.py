import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from uuid import uuid4

from app.api.dependencies import AppResources
from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.api.incidents import router as incident_router
from app.config.paths import PROJECT_ROOT
from app.config.settings import get_settings
from app.demo.seed import FixtureSeedService
from app.persistence.database import Database
from app.services.adapter_status import initial_adapter_status


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    database = Database(settings.database_path)
    connection = database.connect()
    app.state.resources = AppResources(settings=settings, database=database, connection=connection)
    app.state.request_lock = asyncio.Lock()
    app.state.adapter_status = initial_adapter_status(settings.coco_enabled)
    FixtureSeedService(PROJECT_ROOT).seed(connection)
    app.include_router(health_router)
    app.include_router(incident_router)
    app.include_router(demo_router)

    @app.middleware("http")
    async def correlation_header(request: Request, call_next):
        # SQLite uses one shared connection for the local demo. Serialize request
        # handlers so parallel dashboard hydration cannot interleave cursor work.
        async with app.state.request_lock:
            response = await call_next(request)
        response.headers.setdefault("X-Correlation-ID", getattr(request.state, "correlation_id", request.headers.get("X-Correlation-ID", f"corr-api-{uuid4().hex}")))
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": detail.get("code", "http_error"), "message": detail.get("message", "Request failed."), "correlation_id": detail.get("correlation_id", getattr(request.state, "correlation_id", request.headers.get("X-Correlation-ID", f"corr-api-{uuid4().hex}")))}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "The request payload is invalid.", "correlation_id": getattr(request.state, "correlation_id", request.headers.get("X-Correlation-ID", f"corr-api-{uuid4().hex}"))}})

    return app


app = create_app()
