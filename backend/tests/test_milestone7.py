from __future__ import annotations

import json

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
    assert client.post(f"/v1/incidents/{INCIDENT}/validate", headers=OPERATOR).json()["validation"]["status"] == "passed"
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
    status = client.get("/v1/demo/status").json()
    assert status["adapters"]["snowflake_metadata"] == "fixture"
    assert status["adapter_status"]["snowflake_metadata"] == {"mode": "fixture", "status": "available", "source": "fixture", "reason": None}
    assert status["adapter_status"]["decision"]["mode"] == "fixture"
    denied = client.post("/v1/demo/reset", headers=OPERATOR)
    assert denied.status_code == 403


def test_live_coco_investigation_updates_truthful_adapter_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "coco-live.sqlite3"))
    monkeypatch.setenv("PIPELINEPILOT_COCO_ENABLED", "true")
    monkeypatch.setenv("PIPELINEPILOT_COCO_CONNECTION", "pipelinepilot_ro")
    get_settings.cache_clear()

    from app.integrations.coco import CocoCliClient

    def fake_prompt_json(self, prompt: str, *, required_keys: set[str]):
        if "summary" in required_keys:
            return {
                "summary": "CoCo returned sanitized live evidence.",
                "evidence_type": "read_only_context",
                "sanitized_payload": {"contains_pii": False, "adapter": "coco"},
                "citations": [{"document_id": "airflow-live", "title": "Live source", "section": "Read-only result"}],
            }
        evidence_context = prompt.split("Evidence: ", 1)[1].split("\nRunbooks:", 1)[0]
        evidence_ids = [item["id"] for item in json.loads(evidence_context)]
        return {
            "cause": "The live source and staging schemas differ.",
            "confidence_band": "high",
            "evidence_ids": evidence_ids,
            "runbook_ids": ["runbook-schema-drift"],
            "recommended_action": "Apply the controlled fixture recovery.",
            "uncertainty": "Recovery remains fixture-only.",
        }

    monkeypatch.setattr(CocoCliClient, "prompt_json", fake_prompt_json)
    api = TestClient(create_app())

    response = api.post(f"/v1/incidents/{INCIDENT}/investigate", headers=OPERATOR)

    assert response.status_code == 200
    payload = response.json()
    assert payload["adapter_mode"] == "live"
    assert payload["fallback_reason"] is None
    assert all(item["mode"] == "live" for item in payload["evidence"])
    assert all(item["source"] == "coco" for item in payload["adapter_status"].values())
    assert api.get("/v1/demo/status").json()["adapters"]["decision"] == "live"


def test_coco_unavailable_updates_truthful_fallback_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "coco-fallback.sqlite3"))
    monkeypatch.setenv("PIPELINEPILOT_COCO_ENABLED", "true")
    monkeypatch.setenv("PIPELINEPILOT_COCO_COMMAND", "cortex-command-not-installed")
    get_settings.cache_clear()
    api = TestClient(create_app())

    response = api.post(f"/v1/incidents/{INCIDENT}/investigate", headers=OPERATOR)

    assert response.status_code == 200
    payload = response.json()
    assert payload["adapter_mode"] == "fixture"
    assert "CoCo decision unavailable" in payload["fallback_reason"]
    assert payload["adapter_status"]["decision"]["status"] == "degraded"
    assert payload["adapter_status"]["decision"]["source"] == "fixture"
    assert all(item["mode"] == "fixture" for item in payload["evidence"])
    assert api.get("/v1/demo/status").json()["adapters"]["decision"] == "fixture"
