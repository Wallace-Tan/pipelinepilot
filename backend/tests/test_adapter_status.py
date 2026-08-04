from datetime import datetime, timezone

from app.decision.contracts import DecisionResult
from app.domain.contracts import AdapterStatus, ConfidenceBand, Evidence, EvidenceSource, Recommendation, RuntimeMode
from app.services.adapter_status import initial_adapter_status, investigation_adapter_status
from app.skills.contracts import SkillName, SkillResult, SkillStatus


def _evidence(mode: RuntimeMode) -> Evidence:
    return Evidence(
        schema_version="evidence.v1",
        id="ev-status-test",
        incident_id="inc-status-test",
        source=EvidenceSource.SNOWFLAKE_METADATA,
        evidence_type="read_only_schema_context",
        mode=mode,
        summary="Sanitized schema metadata.",
        sanitized_payload={"contains_pii": False},
        collected_at=datetime.now(timezone.utc),
    )


def _decision(adapter_mode: RuntimeMode, fallback_reason: str | None = None) -> DecisionResult:
    recommendation = Recommendation(
        schema_version="recommendation.v1",
        id="rec-status-test",
        incident_id="inc-status-test",
        cause="Schema drift",
        confidence_band=ConfidenceBand.HIGH,
        evidence_ids=["ev-status-test"],
        runbook_ids=["runbook-schema-drift"],
        recommended_action="Apply the controlled fixture recovery.",
        uncertainty="Live ownership is not verified.",
        mode=RuntimeMode.FIXTURE,
    )
    return DecisionResult(
        schema_version="decision_result.v1",
        recommendation=recommendation,
        adapter_mode=adapter_mode,
        fallback_reason=fallback_reason,
    )


def test_initial_coco_status_is_unverified_until_a_call_completes() -> None:
    statuses = initial_adapter_status(True)

    assert statuses["decision"] == AdapterStatus(
        mode="unverified",
        status="not_attempted",
        source="coco",
        reason="CoCo is enabled, but no investigation has completed yet.",
    )


def test_live_context_and_fixture_decision_are_reported_separately() -> None:
    live_skill = SkillResult(
        schema_version="skill_result.v1",
        skill_name=SkillName.SNOWFLAKE_METADATA,
        status=SkillStatus.AVAILABLE,
        evidence=_evidence(RuntimeMode.LIVE),
        adapter_mode=RuntimeMode.LIVE,
    )
    fallback_skill = SkillResult(
        schema_version="skill_result.v1",
        skill_name=SkillName.MONITORING,
        status=SkillStatus.DEGRADED,
        evidence=_evidence(RuntimeMode.FIXTURE),
        adapter_mode=RuntimeMode.FIXTURE,
        degradation_reason="CoCo unavailable; fixture evidence retained.",
    )

    statuses = investigation_adapter_status(
        [live_skill, fallback_skill],
        _decision(RuntimeMode.FIXTURE, "CoCo decision unavailable; fixture fallback selected."),
    )

    assert statuses["snowflake_metadata"].mode == "live"
    assert statuses["snowflake_metadata"].source == "coco"
    assert statuses["monitoring"].status == "degraded"
    assert statuses["monitoring"].source == "fixture"
    assert statuses["decision"].mode == "fixture"
    assert statuses["decision"].reason == "CoCo decision unavailable; fixture fallback selected."
