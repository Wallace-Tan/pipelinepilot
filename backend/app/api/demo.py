from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import correlation_id, require_admin, require_viewer, resources
from app.api.schemas import DemoResetResponse, DemoStatusResponse
from app.domain.contracts import RuntimeMode
from app.demo.seed import FixtureSeedService
from app.persistence.repositories import IncidentRepository
from app.security.identity import RequestIdentity


router = APIRouter(prefix="/v1/demo", tags=["demo"])


@router.get("/status", response_model=DemoStatusResponse)
def demo_status(request: Request, identity: RequestIdentity = Depends(require_viewer)) -> DemoStatusResponse:
    app_resources = resources(request)
    incident = IncidentRepository(app_resources.connection).get("inc-retail-orders-20260723")
    return DemoStatusResponse(
        schema_version="demo_status.v1",
        mode=app_resources.settings.mode,
        fixture="schema_drift",
        incident_id=incident.id if incident else "inc-retail-orders-20260723",
        database_ready=True,
        adapters={"monitoring": "fixture", "airflow_log": "fixture", "dbt": "fixture", "snowflake_metadata": "fixture"},
    )


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo(request: Request, identity: RequestIdentity = Depends(require_admin), correlation: str = Depends(correlation_id)) -> DemoResetResponse:
    app_resources = resources(request)
    if app_resources.settings.mode is not RuntimeMode.FIXTURE:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"code": "fixture_only", "message": "Demo reset is available only in fixture mode.", "correlation_id": correlation})
    app_resources.connection = app_resources.database.reset_fixture(app_resources.connection)
    incident = FixtureSeedService(request.app.state.root).seed(app_resources.connection)
    return DemoResetResponse(
        schema_version="demo_reset.v1",
        incident_id=incident.id,
        mode=incident.mode,
        fixture="schema_drift",
        reset_at=datetime.now(timezone.utc),
        correlation_id=correlation,
    )
