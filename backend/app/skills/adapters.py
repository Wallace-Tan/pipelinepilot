from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.contracts import Evidence, EvidenceSource, RuntimeMode
from app.skills.contracts import ContextSkill, SkillContext, SkillName, SkillResult, SkillStatus


class FixtureContextSkill(ContextSkill):
    def __init__(self, fixture_path: str | Path) -> None:
        self.fixture_path = Path(fixture_path)

    def collect(self, context: SkillContext) -> SkillResult:
        if context.mode is not RuntimeMode.FIXTURE:
            return self._unavailable("fixture adapter requires fixture mode")
        if not self.fixture_path.exists():
            return self._unavailable(f"fixture not found: {self.fixture_path.name}")
        try:
            payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
            evidence = Evidence.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            return self._degraded(f"fixture could not be normalized: {type(error).__name__}")
        if evidence.incident_id != context.incident_id:
            return self._degraded("fixture incident does not match requested incident")
        return SkillResult(
            schema_version="skill_result.v1",
            skill_name=self.name,
            status=SkillStatus.AVAILABLE,
            evidence=evidence,
            adapter_mode=RuntimeMode.FIXTURE,
        )

    def _unavailable(self, reason: str) -> SkillResult:
        return self._result(SkillStatus.UNAVAILABLE, reason)

    def _degraded(self, reason: str) -> SkillResult:
        return self._result(SkillStatus.DEGRADED, reason)

    def _result(self, status: SkillStatus, reason: str) -> SkillResult:
        return SkillResult(
            schema_version="skill_result.v1",
            skill_name=self.name,
            status=status,
            adapter_mode=self.adapter_mode,
            degradation_reason=reason,
        )


class FixtureMonitoringSkill(FixtureContextSkill):
    name = SkillName.MONITORING
    adapter_mode = RuntimeMode.FIXTURE


class FixtureLogInvestigationSkill(FixtureContextSkill):
    name = SkillName.LOG_INVESTIGATION
    adapter_mode = RuntimeMode.FIXTURE


class FixtureDbtHealthSkill(FixtureContextSkill):
    name = SkillName.DBT_HEALTH
    adapter_mode = RuntimeMode.FIXTURE


class FixtureSnowflakeMetadataSkill(FixtureContextSkill):
    name = SkillName.SNOWFLAKE_METADATA
    adapter_mode = RuntimeMode.FIXTURE


def fixture_skills(fixtures_path: str | Path) -> list[ContextSkill]:
    root = Path(fixtures_path)
    return [
        FixtureMonitoringSkill(root / "monitoring_status.json"),
        FixtureLogInvestigationSkill(root / "airflow_parser_log.json"),
        FixtureDbtHealthSkill(root / "dbt_context.json"),
        FixtureSnowflakeMetadataSkill(root / "snowflake_metadata.json"),
    ]
