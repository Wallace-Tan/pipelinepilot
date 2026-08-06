from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.decision.adapters import CocoDecisionAdapter, FixtureDecisionAdapter
from app.domain.contracts import Evidence, Incident, RuntimeMode
from app.knowledge.services import KnowledgeRepository, RecommendationService
from app.integrations.coco import CocoCliClient, CocoCliError
from app.skills.adapters import coco_skills
from app.skills.contracts import SkillContext, SkillStatus


ROOT = Path(__file__).resolve().parents[2]


def test_coco_client_extracts_structured_json_from_stream_output(monkeypatch) -> None:
    response = {"summary": "run failed", "evidence_type": "run_status"}

    def fake_run(args, **kwargs):
        assert args[:3] == ["cortex", "--connection", "demo"]
        assert args[3:8] == ["--no-auto-update", "--sql-read-only", "--allowed-tools", "SQL", "--print"]
        assert "--print" in args
        assert kwargs["timeout"] == 12
        return SimpleNamespace(returncode=0, stdout=json.dumps({"type": "assistant", "text": json.dumps(response)}))

    monkeypatch.setattr("app.integrations.coco.subprocess.run", fake_run)
    client = CocoCliClient(connection="demo", timeout_seconds=12)

    assert client.prompt_json("inspect the incident", required_keys={"summary", "evidence_type"}) == response


def test_coco_client_extracts_fenced_json_from_stream_output(monkeypatch) -> None:
    response = {"summary": "run failed", "evidence_type": "run_status"}

    def fake_run(args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"type": "result", "result": f"```json\n{json.dumps(response)}\n```"}),
        )

    monkeypatch.setattr("app.integrations.coco.subprocess.run", fake_run)

    assert CocoCliClient().prompt_json("inspect the incident", required_keys={"summary", "evidence_type"}) == response


def test_coco_client_fails_closed_on_cli_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.integrations.coco.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=3, stdout="", stderr="connection failed"),
    )

    with pytest.raises(CocoCliError, match="status 3"):
        CocoCliClient().prompt_json("inspect the incident", required_keys={"summary"})


def test_coco_context_retains_fixture_evidence_when_cli_is_unavailable() -> None:
    skill = coco_skills(CocoCliClient(command="cortex-command-not-installed"), ROOT / "data/fixtures/schema_drift")[0]
    result = skill.collect(
        SkillContext(
            schema_version="skill_context.v1",
            incident_id="inc-retail-orders-20260723",
            pipeline_name="retail_orders_daily",
            run_id="airflow-run-20260723T040000Z",
            mode=RuntimeMode.FIXTURE,
        )
    )

    assert result.status is SkillStatus.DEGRADED
    assert result.evidence is not None
    assert "fixture evidence retained" in (result.degradation_reason or "")


def test_coco_decision_rejects_uncited_evidence_and_uses_fixture_fallback() -> None:
    incident = Incident.model_validate(json.loads((ROOT / "data/fixtures/schema_drift/incident.json").read_text(encoding="utf-8")))
    evidence = [
        Evidence.model_validate(json.loads(path.read_text(encoding="utf-8"))).model_copy(update={"mode": RuntimeMode.LIVE})
        for path in (ROOT / "data/fixtures/schema_drift").glob("*.json")
        if path.name not in {"incident.json", "expected_recommendation.json"}
    ]

    class InvalidCitationClient:
        def prompt_json(self, prompt: str, *, required_keys: set[str]):
            return {
                "cause": "Unsupported claim",
                "confidence_band": "high",
                "evidence_ids": ["ev-not-available"],
                "runbook_ids": ["runbook-schema-drift"],
                "recommended_action": "Run the recovery.",
                "uncertainty": "Unknown.",
            }

    runbooks = KnowledgeRepository(ROOT / "data/runbooks")
    fallback = FixtureDecisionAdapter(RecommendationService(ROOT / "data/fixtures/schema_drift/expected_recommendation.json", runbooks))
    result = CocoDecisionAdapter(InvalidCitationClient(), runbooks, fallback).decide(incident, evidence)

    assert result.adapter_mode is RuntimeMode.FIXTURE
    assert result.recommendation.evidence_ids
    assert "CoCo decision unavailable" in (result.fallback_reason or "")
