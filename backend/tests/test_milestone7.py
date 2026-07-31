from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.config.settings import get_settings
from app.main import create_app


INCIDENT = "inc-retail-orders-20260723"
OPERATOR = {"X-Actor-Id": "operator-e2e", "X-Actor-Role": "operator"}
ADMIN = {"X-Actor-Id": "admin-e2e", "X-Actor-Role": "admin"}
VIEWER = {"X-Actor-Id": "viewer-e2e", "X-Actor-Role": "viewer"}


def client_for(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "milestone7.sqlite3"))
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def api_client(tmp_path, monkeypatch) -> TestClient:
    return client_for(tmp_path, monkeypatch)


def investigate(client: TestClient) -> None:
    response = client.post(f"/v1/incidents/{INCIDENT}/investigate", headers=OPERATOR)
    assert response.status_code == 200


def approve_and_execute(client: TestClient, key: str = "m7-lifecycle-001") -> None:
    headers = {**OPERATOR, "Idempotency-Key": key}
    approval = client.post(f"/v1/incidents/{INCIDENT}/approvals", headers=headers, json={"action": "schema_drift_recovery"})
    assert approval.status_code == 200
    execution = client.post(f"/v1/incidents/{INCIDENT}/executions", headers=headers, json={"action": "schema_drift_recovery"})
    assert execution.status_code == 200


def test_full_lifecycle_and_feedback_are_reported(api_client) -> None:
    client = api_client
    assert client.get("/v1/incidents", headers=VIEWER).json()["items"][0]["status"] == "created"
    investigate(client)
    detail = client.get(f"/v1/incidents/{INCIDENT}", headers=VIEWER).json()
    assert detail["policy_decision"]["decision"] == "approval_required"
    assert detail["recommendation"]["runbook_ids"] == ["runbook-schema-drift"]
    approve_and_execute(client)
    assert client.post(f"/v1/incidents/{INCIDENT}/validate", headers=OPERATOR).json()["status"] == "passed"
    feedback = client.post(f"/v1/incidents/{INCIDENT}/feedback", headers=OPERATOR, json={"correction": "Keep the staging contract check in the release checklist.", "outcome": "accepted"})
    assert feedback.status_code == 200
    report = client.get(f"/v1/incidents/{INCIDENT}/report", headers=VIEWER)
    assert report.status_code == 200
    assert report.json()["incident"]["status"] == "validated"
    assert report.json()["feedback_count"] == 1
    assert any(event["action"] == "feedback.created" for event in report.json()["audit"])


def test_viewer_mutations_return_safe_errors(api_client) -> None:
    client = api_client
    for path, body in (
        (f"/v1/incidents/{INCIDENT}/investigate", None),
        (f"/v1/incidents/{INCIDENT}/approvals", {"action": "schema_drift_recovery"}),
        (f"/v1/incidents/{INCIDENT}/executions", {"action": "schema_drift_recovery"}),
        (f"/v1/incidents/{INCIDENT}/validate", None),
        (f"/v1/incidents/{INCIDENT}/feedback", {"correction": "x", "outcome": "x"}),
    ):
        response = client.post(path, headers=VIEWER, json=body)
        assert response.status_code == 403
        assert set(response.json()["error"]) == {"code", "message", "correlation_id"}


def test_missing_approval_is_blocked_and_reset_is_repeatable(api_client) -> None:
    client = api_client
    investigate(client)
    blocked = client.post(f"/v1/incidents/{INCIDENT}/executions", headers={**OPERATOR, "Idempotency-Key": "m7-blocked-001"}, json={"action": "schema_drift_recovery"})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "approval_required"
    assert client.get(f"/v1/incidents/{INCIDENT}").json()["executions"][0]["status"] == "blocked"
    reset = client.post("/v1/demo/reset", headers=ADMIN)
    assert reset.status_code == 200
    assert client.get(f"/v1/incidents/{INCIDENT}").json()["incident"]["status"] == "created"
    assert client.get(f"/v1/incidents/{INCIDENT}").json()["executions"] == []
    assert client.post("/v1/demo/reset", headers=ADMIN).status_code == 200


def test_reset_and_status_are_role_and_mode_safe(api_client) -> None:
    client = api_client
    assert client.get("/v1/demo/status").json()["adapters"]["snowflake_metadata"] == "fixture"
    denied = client.post("/v1/demo/reset", headers=OPERATOR)
    assert denied.status_code == 403
