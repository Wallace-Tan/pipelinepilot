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
