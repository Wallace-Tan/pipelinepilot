from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import create_app


def test_current_policy_is_typed_and_viewer_readable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "milestone8.sqlite3"))
    get_settings.cache_clear()
    client = TestClient(create_app())

    responses = [
        client.get("/v1/policies/current", headers={"X-Actor-Id": f"{role}-m8", "X-Actor-Role": role})
        for role in ("viewer", "operator", "admin")
    ]

    assert all(response.status_code == 200 for response in responses)
    policy = responses[0].json()["policy"]
    assert policy["schema_version"] == "policy.v1"
    assert policy["id"] == "policy-demo-2026-07"
    assert policy["version"] == "2026.07-demo"
    assert policy["mode"] == "fixture"
    assert policy["immutable"] is True
    assert policy["default_decision"] == "deny"

    rules = {rule["id"]: rule for rule in policy["rules"]}
    assert rules["rule-fixture-schema-drift-recovery"]["decision"] == "approval_required"
    assert rules["rule-fixture-schema-drift-recovery"]["required_approver_role"] == "operator"
    assert rules["rule-fixture-read-only-investigation"]["decision"] == "allow"


def test_audit_index_is_admin_only_and_filterable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "audit-index.sqlite3"))
    get_settings.cache_clear()
    client = TestClient(create_app())
    operator = {"X-Actor-Id": "operator-m8", "X-Actor-Role": "operator"}
    admin = {"X-Actor-Id": "admin-m8", "X-Actor-Role": "admin"}

    denied = client.get("/v1/audit-logs", headers=operator)
    allowed = client.get("/v1/audit-logs", headers=admin, params={"action": "incident.created"})

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert all(item["action"] == "incident.created" for item in allowed.json()["items"])


def test_incident_queue_is_seeded_and_filterable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "incident-queue.sqlite3"))
    get_settings.cache_clear()
    client = TestClient(create_app())
    viewer = {"X-Actor-Id": "viewer-queue", "X-Actor-Role": "viewer"}

    response = client.get("/v1/incidents", headers=viewer, params={"severity": "critical"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "inc-warehouse-permission-20260723"


def test_agent_and_execution_detail_resources_are_typed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "detail-resources.sqlite3"))
    get_settings.cache_clear()
    client = TestClient(create_app())
    operator = {"X-Actor-Id": "operator-detail", "X-Actor-Role": "operator"}
    viewer = {"X-Actor-Id": "viewer-detail", "X-Actor-Role": "viewer"}
    incident_id = "inc-retail-orders-20260723"

    assert client.post(f"/v1/incidents/{incident_id}/investigate", headers=operator).status_code == 200
    agent = client.get(f"/v1/incidents/{incident_id}/agent", headers=viewer)
    assert agent.status_code == 200
    assert agent.json()["recommendation"]["schema_version"] == "recommendation.v2"
    assert agent.json()["adapter_status"]

    key = "detail-resource-execution"
    action = {"action": "schema_drift_recovery"}
    headers = {**operator, "Idempotency-Key": key}
    assert client.post(f"/v1/incidents/{incident_id}/approvals", headers=headers, json=action).status_code == 200
    execution_response = client.post(f"/v1/incidents/{incident_id}/executions", headers=headers, json=action)
    assert execution_response.status_code == 200
    execution_id = execution_response.json()["execution"]["id"]
    assert client.post(f"/v1/incidents/{incident_id}/validate", headers=operator).status_code == 200

    execution = client.get(f"/v1/incidents/{incident_id}/executions/{execution_id}", headers=viewer)
    assert execution.status_code == 200
    assert execution.json()["execution"]["status"] == "succeeded"
    assert execution.json()["approval"]["decision"] == "approved"
    assert execution.json()["validation"]["status"] == "passed"
