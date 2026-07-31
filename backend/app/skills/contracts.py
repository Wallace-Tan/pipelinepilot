from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol

from app.domain.contracts import Evidence, RuntimeMode, SafeId, StrictContract


class SkillName(StrEnum):
    MONITORING = "monitoring"
    LOG_INVESTIGATION = "log_investigation"
    DBT_HEALTH = "dbt_health"
    SNOWFLAKE_METADATA = "snowflake_metadata"


class SkillStatus(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class SkillContext(StrictContract):
    schema_version: Literal["skill_context.v1"]
    incident_id: SafeId
    pipeline_name: str
    run_id: SafeId
    mode: RuntimeMode


class SkillResult(StrictContract):
    schema_version: Literal["skill_result.v1"]
    skill_name: SkillName
    status: SkillStatus
    evidence: Evidence | None = None
    adapter_mode: RuntimeMode
    degradation_reason: str | None = None


class ContextSkill(Protocol):
    name: SkillName
    adapter_mode: RuntimeMode

    def collect(self, context: SkillContext) -> SkillResult:
        """Collect normalized, sanitized-ready context for an incident."""
