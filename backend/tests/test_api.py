import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app


def test_api_supports_seeded_governed_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "api.sqlite3"))
    get_settings.cache_clear()
    from app.main import create_app
    client = TestClient(create_app())
    actor = {"X-Actor-Id": "operator-api", "X-Actor-Role": "operator"}
    incident_id = "inc-retail-orders-20260723"

    assert client.get("/v1/incidents").status_code == 200
    assert client.post(f"/v1/incidents/{incident_id}/investigate", headers=actor).status_code == 200
    key = "api-lifecycle-001"
    approval = client.post(f"/v1/incidents/{incident_id}/approvals", headers={**actor, "Idempotency-Key": key}, json={"action": "schema_drift_recovery", "reason": "Approve fixture recovery."})
    assert approval.status_code == 200
    execution = client.post(f"/v1/incidents/{incident_id}/executions", headers={**actor, "Idempotency-Key": key}, json={"action": "schema_drift_recovery"})
    assert execution.status_code == 200
    assert client.post(f"/v1/incidents/{incident_id}/validate", headers=actor).status_code == 200
    report = client.get(f"/v1/incidents/{incident_id}/report")
    assert report.status_code == 200
    assert report.json()["incident"]["status"] == "validated"


def test_api_enforces_viewer_and_error_envelope() -> None:
    client = TestClient(app)
    response = client.post("/v1/incidents/inc-retail-orders-20260723/investigate")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"
    assert response.json()["error"]["correlation_id"]
