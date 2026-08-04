from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.contracts import Evidence, EvidenceCitation, EvidenceSource, RuntimeMode
from app.integrations.coco import CocoCliClient, CocoCliError
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


class CocoContextSkill(ContextSkill):
    adapter_mode = RuntimeMode.LIVE

    _source_by_name = {
        SkillName.MONITORING: EvidenceSource.MONITORING,
        SkillName.LOG_INVESTIGATION: EvidenceSource.AIRFLOW_LOG,
        SkillName.DBT_HEALTH: EvidenceSource.DBT,
        SkillName.SNOWFLAKE_METADATA: EvidenceSource.SNOWFLAKE_METADATA,
    }

    def __init__(self, name: SkillName, client: CocoCliClient, fallback: ContextSkill | None = None) -> None:
        self.name = name
        self.client = client
        self.fallback = fallback

    def collect(self, context: SkillContext) -> SkillResult:
        try:
            value = self.client.prompt_json(
                self._prompt(context),
                required_keys={"summary", "evidence_type", "sanitized_payload", "citations"},
            )
            evidence = Evidence(
                schema_version="evidence.v1",
                id=f"coco-{self.name.value}-{context.incident_id}",
                incident_id=context.incident_id,
                source=self._source_by_name[self.name],
                evidence_type=str(value["evidence_type"]),
                mode=RuntimeMode.LIVE,
                summary=str(value["summary"]),
                sanitized_payload=dict(value["sanitized_payload"]),
                citations=[EvidenceCitation.model_validate(item) for item in value["citations"]],
                collected_at=datetime.now(timezone.utc),
            )
        except (CocoCliError, KeyError, TypeError, ValueError, ValidationError) as error:
            if self.fallback is not None:
                fallback_result = self.fallback.collect(context)
                return fallback_result.model_copy(
                    update={
                        "status": SkillStatus.DEGRADED,
                        "degradation_reason": f"CoCo unavailable ({type(error).__name__}); fixture evidence retained.",
                    }
                )
            return SkillResult(
                schema_version="skill_result.v1",
                skill_name=self.name,
                status=SkillStatus.UNAVAILABLE,
                adapter_mode=self.adapter_mode,
                degradation_reason=f"CoCo context unavailable: {type(error).__name__}.",
            )
        return SkillResult(
            schema_version="skill_result.v1",
            skill_name=self.name,
            status=SkillStatus.AVAILABLE,
            evidence=evidence,
            adapter_mode=self.adapter_mode,
        )

    def _prompt(self, context: SkillContext) -> str:
        source_instruction = {
            SkillName.MONITORING: "Inspect the Airflow DAG run state and task status.",
            SkillName.LOG_INVESTIGATION: "Inspect the Airflow task logs and extract the safe error signature.",
            SkillName.DBT_HEALTH: "Inspect the dbt model, test, freshness, and lineage signals available for this run.",
            SkillName.SNOWFLAKE_METADATA: "Use read-only Snowflake metadata queries to compare the source and staging schemas.",
        }[self.name]
        return f"""You are a read-only PipelinePilot evidence skill. {source_instruction}
Never trigger, pause, retry, mutate, or delete anything. Do not return secrets, tokens, email addresses, card numbers, or raw personal identifiers.
Return exactly one JSON object with these keys:
{{"summary": "short evidence summary", "evidence_type": "stable type name", "sanitized_payload": {{}}, "citations": [{{"document_id": "runbook-or-source-id", "title": "source title", "section": "section"}}]}}
Use only the incident context below and the connected Airflow/Snowflake resources.
Incident ID: {context.incident_id}
Pipeline: {context.pipeline_name}
Run ID: {context.run_id}
"""


def coco_skills(client: CocoCliClient, fixtures_path: str | Path | None = None) -> list[ContextSkill]:
    fixture_by_name = {skill.name: skill for skill in fixture_skills(fixtures_path)} if fixtures_path else {}
    return [CocoContextSkill(name, client, fixture_by_name.get(name)) for name in SkillName]
