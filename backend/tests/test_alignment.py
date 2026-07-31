from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.decision.adapters import FixtureDecisionAdapter
from app.domain.contracts import ActorRole, Evidence, Incident, IncidentStatus, PolicyDecisionType, RiskLevel
from app.knowledge.services import KnowledgeRepository, RecommendationService
from app.main import create_app
from app.policy.engine import PolicyEngine


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data/fixtures/schema_drift"
POLICY = ROOT / "data/policies/demo_policy.json"


def incident() -> Incident:
    return Incident.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))


def evidence() -> list[Evidence]:
    return [Evidence.model_validate(json.loads(path.read_text(encoding="utf-8"))) for path in FIXTURES.glob("*.json") if path.name not in {"incident.json", "expected_recommendation.json"}]


def test_policy_uses_severity_and_retry_count() -> None:
    engine = PolicyEngine.from_path(POLICY)
    assert engine.evaluate(incident(), "schema_drift_recovery", ActorRole.OPERATOR).decision is PolicyDecisionType.APPROVAL_REQUIRED
    assert engine.evaluate(incident(), "schema_drift_recovery", ActorRole.OPERATOR, retry_count=1).decision is PolicyDecisionType.DENY
    low = incident().model_copy(update={"severity": RiskLevel.MEDIUM})
    assert engine.evaluate(low, "schema_drift_recovery", ActorRole.OPERATOR).decision is PolicyDecisionType.DENY


def test_fixture_decision_adapter_is_explicit_fallback() -> None:
    adapter = FixtureDecisionAdapter(RecommendationService(FIXTURES / "expected_recommendation.json", KnowledgeRepository(ROOT / "data/runbooks")))
    result = adapter.decide(incident(), evidence())
    assert result.adapter_mode.value == "fixture"
    assert result.fallback_reason


def test_recommendation_rejects_malformed_and_unmatched_knowledge(tmp_path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        RecommendationService(malformed, KnowledgeRepository(ROOT / "data/runbooks")).recommend(incident(), evidence())
    empty = RecommendationService(FIXTURES / "expected_recommendation.json", KnowledgeRepository(tmp_path))
    with pytest.raises(ValueError, match="runbook citation"):
        empty.recommend(incident(), evidence())


def test_api_rejection_report_and_correlation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "alignment.sqlite3"))
    get_settings.cache_clear()
    client = TestClient(create_app())
    operator = {"X-Actor-Id": "alignment-operator", "X-Actor-Role": "operator", "Idempotency-Key": "alignment-approval-001"}
    incident_id = "inc-retail-orders-20260723"
    assert client.post(f"/v1/incidents/{incident_id}/investigate", headers=operator).headers["X-Correlation-ID"]
    rejected = client.post(f"/v1/incidents/{incident_id}/approvals", headers=operator, json={"action": "schema_drift_recovery", "approved": False, "reason": "Not approved."})
    assert rejected.status_code == 200
    assert rejected.json()["approval"]["decision"] == "rejected"
    assert rejected.json()["correlation_id"] == rejected.headers["X-Correlation-ID"]
    replay = client.post(f"/v1/incidents/{incident_id}/approvals", headers=operator, json={"action": "schema_drift_recovery", "approved": False, "reason": "Not approved."})
    assert replay.status_code == 200
    conflict = client.post(f"/v1/incidents/{incident_id}/approvals", headers=operator, json={"action": "unknown_action", "approved": False, "reason": "Changed request."})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    report = client.get(f"/v1/incidents/{incident_id}/report")
    assert report.json()["policy_decision"]["decision"] == "approval_required"
    assert report.json()["execution"] is not None
