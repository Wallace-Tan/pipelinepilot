import json
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.contracts import Incident, RuntimeMode
from app.skills.adapters import (
    FixtureContextSkill,
    FixtureDbtHealthSkill,
    FixtureLogInvestigationSkill,
    FixtureMonitoringSkill,
    FixtureSnowflakeMetadataSkill,
    fixture_skills,
)
from app.skills.contracts import SkillContext, SkillName, SkillResult, SkillStatus
from app.skills.coordinator import SkillCoordinator


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "data" / "fixtures" / "schema_drift"


def context() -> SkillContext:
    return SkillContext(
        schema_version="skill_context.v1",
        incident_id="inc-retail-orders-20260723",
        pipeline_name="retail_orders_daily",
        run_id="airflow-run-20260723T040000Z",
        mode=RuntimeMode.FIXTURE,
    )


def test_skill_contract_rejects_unknown_fields_and_invalid_status() -> None:
    payload = {
        "schema_version": "skill_result.v1",
        "skill_name": "monitoring",
        "status": "available",
        "adapter_mode": "fixture",
        "unexpected": True,
    }
    with pytest.raises(ValidationError):
        SkillResult.model_validate(payload)

    payload.pop("unexpected")
    payload["status"] = "complete"
    with pytest.raises(ValidationError):
        SkillResult.model_validate(payload)


def test_fixture_adapters_return_normalized_evidence() -> None:
    skills = fixture_skills(FIXTURES)
    results = [skill.collect(context()) for skill in skills]

    assert {result.skill_name for result in results} == {
        SkillName.MONITORING,
        SkillName.LOG_INVESTIGATION,
        SkillName.DBT_HEALTH,
        SkillName.SNOWFLAKE_METADATA,
    }
    assert all(result.status is SkillStatus.AVAILABLE for result in results)
    assert all(result.evidence is not None for result in results)
    assert all(result.evidence.incident_id == context().incident_id for result in results if result.evidence)


def test_fixture_adapter_reports_missing_and_malformed_data(tmp_path) -> None:
    missing = FixtureMonitoringSkill(tmp_path / "missing.json").collect(context())
    assert missing.status is SkillStatus.UNAVAILABLE
    assert missing.evidence is None

    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text(json.dumps({"not": "evidence"}), encoding="utf-8")
    malformed = FixtureContextSkill(malformed_path)
    malformed.name = SkillName.MONITORING
    malformed.adapter_mode = RuntimeMode.FIXTURE
    result = malformed.collect(context())
    assert result.status is SkillStatus.DEGRADED
    assert result.degradation_reason


class SlowSkill:
    name = SkillName.MONITORING
    adapter_mode = RuntimeMode.FIXTURE

    def collect(self, skill_context: SkillContext) -> SkillResult:
        time.sleep(0.05)
        return SkillResult(
            schema_version="skill_result.v1",
            skill_name=self.name,
            status=SkillStatus.AVAILABLE,
            adapter_mode=RuntimeMode.FIXTURE,
        )


def test_coordinator_returns_unavailable_result_on_timeout() -> None:
    results = SkillCoordinator([SlowSkill()], timeout_seconds=0.001).collect(context())

    assert len(results) == 1
    assert results[0].status is SkillStatus.UNAVAILABLE
    assert results[0].degradation_reason == "skill timed out"
