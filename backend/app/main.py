from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path

from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.api.incidents import router as incident_router, ROOT
from app.config.settings import get_settings
from app.demo.seed import FixtureSeedService
from app.persistence.database import Database


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    database = Database(settings.database_path)
    connection = database.connect()
    app.state.resources = type("Resources", (), {"settings": settings, "database": database, "connection": connection})()
    app.state.root = ROOT
    FixtureSeedService(ROOT).seed(connection)
    app.include_router(health_router)
    app.include_router(incident_router)
    app.include_router(demo_router)

    @app.middleware("http")
    async def correlation_header(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Correlation-ID", request.headers.get("X-Correlation-ID", "corr-api-response"))
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": detail.get("code", "http_error"), "message": detail.get("message", "Request failed."), "correlation_id": detail.get("correlation_id", request.headers.get("X-Correlation-ID", "corr-api-error"))}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "The request payload is invalid.", "correlation_id": request.headers.get("X-Correlation-ID", "corr-api-validation")}})

    return app


app = create_app()
