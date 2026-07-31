from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path

from app.api.health import router as health_router
from app.api.incidents import router as incident_router, ROOT
from app.config.settings import get_settings
from app.persistence.database import Database
from app.persistence.repositories import IncidentRepository, PolicyRepository
from app.domain.contracts import Incident, PolicyDocument


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    database = Database(settings.database_path)
    connection = database.connect()
    app.state.resources = type("Resources", (), {"settings": settings, "database": database, "connection": connection})()
    _seed_fixture(connection)
    app.include_router(health_router)
    app.include_router(incident_router)

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


def _seed_fixture(connection) -> None:
    incident = Incident.model_validate(__import__("json").loads((ROOT / "data/fixtures/schema_drift/incident.json").read_text(encoding="utf-8")))
    IncidentRepository(connection).save(incident)
    policy = PolicyDocument.model_validate(__import__("json").loads((ROOT / "data/policies/demo_policy.json").read_text(encoding="utf-8")))
    PolicyRepository(connection).save(policy)


app = create_app()
