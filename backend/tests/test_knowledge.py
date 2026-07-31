import json
from pathlib import Path

import pytest

from app.domain.contracts import Evidence, Incident
from app.knowledge.services import KnowledgeRepository, RecommendationService


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data/fixtures/schema_drift"


def fixture_incident() -> Incident:
    return Incident.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))


def fixture_evidence() -> list[Evidence]:
    return [Evidence.model_validate(json.loads(path.read_text(encoding="utf-8"))) for path in FIXTURES.glob("*.json") if path.name not in {"incident.json", "expected_recommendation.json"}]


def test_fixture_recommendation_is_typed_and_cited() -> None:
    service = RecommendationService(FIXTURES / "expected_recommendation.json", KnowledgeRepository(ROOT / "data/runbooks"))
    recommendation = service.recommend(fixture_incident(), fixture_evidence())
    assert recommendation.runbook_ids == ["runbook-schema-drift"]
    assert recommendation.evidence_ids


def test_recommendation_rejects_missing_evidence(tmp_path) -> None:
    payload = json.loads((FIXTURES / "expected_recommendation.json").read_text(encoding="utf-8"))
    payload["evidence_ids"] = ["ev-missing"]
    path = tmp_path / "recommendation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    service = RecommendationService(path, KnowledgeRepository(ROOT / "data/runbooks"))
    with pytest.raises(ValueError, match="unavailable evidence"):
        service.recommend(fixture_incident(), fixture_evidence())
