from __future__ import annotations

from app.decision.contracts import DecisionResult
from app.domain.contracts import AdapterStatus, RuntimeMode
from app.skills.contracts import SkillResult, SkillStatus


def initial_adapter_status(coco_enabled: bool) -> dict[str, AdapterStatus]:
    if coco_enabled:
        return {
            name: AdapterStatus(
                mode="unverified",
                status="not_attempted",
                source="coco",
                reason="CoCo is enabled, but no investigation has completed yet.",
            )
            for name in (*_skill_names(), "decision")
        }
    return {
        name: AdapterStatus(mode=RuntimeMode.FIXTURE.value, status="available", source="fixture")
        for name in (*_skill_names(), "decision")
    }


def investigation_adapter_status(
    skill_results: list[SkillResult], decision: DecisionResult,
) -> dict[str, AdapterStatus]:
    statuses = {
        result.skill_name.value: _skill_status(result)
        for result in skill_results
    }
    statuses["decision"] = _decision_status(decision)
    return statuses


def adapter_modes(statuses: dict[str, AdapterStatus]) -> dict[str, str]:
    return {name: value.mode for name, value in statuses.items()}


def _skill_status(result: SkillResult) -> AdapterStatus:
    mode = result.evidence.mode.value if result.evidence is not None else result.adapter_mode.value
    source = "coco" if result.adapter_mode is RuntimeMode.LIVE else "fixture"
    return AdapterStatus(
        mode=mode,
        status=result.status.value,
        source=source,
        reason=result.degradation_reason,
    )


def _decision_status(result: DecisionResult) -> AdapterStatus:
    if result.adapter_mode is RuntimeMode.LIVE:
        return AdapterStatus(mode=RuntimeMode.LIVE.value, status="available", source="coco")
    return AdapterStatus(
        mode=result.adapter_mode.value,
        status="degraded" if result.fallback_reason else "available",
        source="fixture",
        reason=result.fallback_reason,
    )


def _skill_names() -> tuple[str, ...]:
    return ("monitoring", "log_investigation", "dbt_health", "snowflake_metadata")
