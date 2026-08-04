from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.contracts import RuntimeMode
from app.integrations.coco import CocoCliClient, CocoCliError
from app.skills.adapters import coco_skills
from app.skills.contracts import SkillContext, SkillStatus


ROOT = Path(__file__).resolve().parents[2]


def test_coco_client_extracts_structured_json_from_stream_output(monkeypatch) -> None:
    response = {"summary": "run failed", "evidence_type": "run_status"}

    def fake_run(args, **kwargs):
        assert args[:3] == ["cortex", "--connection", "demo"]
        assert "--print" in args
        assert kwargs["timeout"] == 12
        return SimpleNamespace(returncode=0, stdout=json.dumps({"type": "assistant", "text": json.dumps(response)}))

    monkeypatch.setattr("app.integrations.coco.subprocess.run", fake_run)
    client = CocoCliClient(connection="demo", timeout_seconds=12)

    assert client.prompt_json("inspect the incident", required_keys={"summary", "evidence_type"}) == response


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
