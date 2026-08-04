from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import correlation_id, idempotency_key, remember_idempotent, replay_idempotent, require_admin, require_viewer, resources
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
    try:
        app_resources.connection.execute("SELECT 1").fetchone()
        database_ready = True
    except Exception:
        database_ready = False
    fixture_root = request.app.state.root / "data/fixtures/schema_drift"
    adapter_mode = "coco" if app_resources.settings.coco_enabled else "fixture"
    adapters = {
        name: adapter_mode if (fixture_root / filename).exists() else "unavailable"
        for name, filename in {
            "monitoring": "monitoring_status.json",
            "airflow_log": "airflow_parser_log.json",
            "dbt": "dbt_context.json",
            "snowflake_metadata": "snowflake_metadata.json",
        }.items()
    }
    adapters["decision"] = adapter_mode
    return DemoStatusResponse(
        schema_version="demo_status.v1",
        mode=app_resources.settings.mode,
        fixture="schema_drift",
        incident_id=incident.id if incident else "inc-retail-orders-20260723",
        database_ready=database_ready,
        adapters=adapters,
    )


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo(request: Request, identity: RequestIdentity = Depends(require_admin), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)) -> DemoResetResponse:
    replay = replay_idempotent(request, key, "demo.reset", {"fixture": "schema_drift"}, DemoResetResponse)
    if replay is not None:
        return replay
    app_resources = resources(request)
    if app_resources.settings.mode is not RuntimeMode.FIXTURE:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"code": "fixture_only", "message": "Demo reset is available only in fixture mode.", "correlation_id": correlation})
    app_resources.connection = app_resources.database.reset_fixture(app_resources.connection)
    incident = FixtureSeedService(request.app.state.root).seed(app_resources.connection)
    response = DemoResetResponse(
        schema_version="demo_reset.v1",
        incident_id=incident.id,
        mode=incident.mode,
        fixture="schema_drift",
        reset_at=datetime.now(timezone.utc),
        correlation_id=correlation,
    )
    remember_idempotent(request, key, "demo.reset", {"fixture": "schema_drift"}, response)
    return response
