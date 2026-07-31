import json
from pathlib import Path

import pytest

from app.domain.contracts import (
    ActorRole,
    Incident,
    IncidentStatus,
    PolicyDecisionType,
    RecoveryExecutionStatus,
    RiskLevel,
    RuntimeMode,
    ValidationStatus,
)
from app.persistence.database import Database
from app.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    ExecutionRepository,
    IncidentRepository,
)
from app.policy.engine import PolicyEngine
from app.security.identity import identity_from_headers
from app.services.errors import GovernanceError
from app.services.governance import ApprovalService, build_execution_proposal
from app.services.recovery import FixtureValidationSkill, RecoveryService, ValidationService


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "data" / "policies" / "demo_policy.json"


def make_incident(incident_id: str = "inc-governance-001") -> Incident:
    return Incident(
        schema_version="incident.v1",
        id=incident_id,
        pipeline_name="retail_orders_daily",
        run_id=f"run-{incident_id}",
        mode=RuntimeMode.FIXTURE,
        status=IncidentStatus.INVESTIGATED,
        severity=RiskLevel.HIGH,
        summary="Schema drift governance test",
        detected_at="2026-07-23T04:18:00Z",
        evidence_ids=["ev-test-001", "ev-test-002"],
    )


def repos(tmp_path, incident: Incident):
    database = Database(tmp_path / "governance.sqlite3")
    connection = database.connect()
    incident_repository = IncidentRepository(connection)
    incident_repository.save(incident)
    return (
        database,
        incident_repository,
        ExecutionRepository(connection),
        ApprovalRepository(connection),
        AuditRepository(connection),
    )


def test_policy_engine_evaluates_roles_and_defaults_to_deny() -> None:
    engine = PolicyEngine.from_path(POLICY_PATH)
    incident = make_incident()

    operator_decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    admin_decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.ADMIN)
    viewer_decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.VIEWER)
    read_only_decision = engine.evaluate(incident, "read_only_investigation", ActorRole.VIEWER)
    unknown_decision = engine.evaluate(incident, "unknown_action", ActorRole.ADMIN)

    assert operator_decision.decision is PolicyDecisionType.APPROVAL_REQUIRED
    assert admin_decision.decision is PolicyDecisionType.APPROVAL_REQUIRED
    assert viewer_decision.decision is PolicyDecisionType.DENY
    assert read_only_decision.decision is PolicyDecisionType.ALLOW
    assert unknown_decision.decision is PolicyDecisionType.DENY

    invalid_engine = PolicyEngine.from_path(REPO_ROOT / "missing-policy.json")
    assert invalid_engine.evaluate(incident, "schema_drift_recovery", ActorRole.ADMIN).decision is PolicyDecisionType.DENY


def test_approval_binds_proposal_and_allows_admin(tmp_path) -> None:
    incident = make_incident()
    database, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.ADMIN)
    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-001", decision)
    service = ApprovalService(incident_repository, execution_repository, approval_repository, audit_repository)

    approval = service.create(
        incident,
        proposal,
        decision,
        identity_from_headers("admin-1", "admin"),
        "Approve controlled fixture recovery.",
    )

    assert approval.actor_role is ActorRole.ADMIN
    assert approval.request_fingerprint == proposal.request_fingerprint
    assert incident_repository.get(incident.id).status is IncidentStatus.APPROVED
    assert execution_repository.get_by_idempotency_key("idem-governance-001").approval_id == approval.id
    assert database.connect().execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 2


def test_viewer_cannot_approve_and_changed_evidence_invalidates_proposal(tmp_path) -> None:
    incident = make_incident()
    _, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    service = ApprovalService(incident_repository, execution_repository, approval_repository, audit_repository)

    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-002", decision)
    with pytest.raises(GovernanceError, match="Only Operator or Admin"):
        service.create(incident, proposal, decision, identity_from_headers(None, None), "viewer cannot approve")

    changed_incident = incident.model_copy(update={"evidence_ids": ["ev-test-003"]})
    with pytest.raises(GovernanceError, match="evidence snapshot"):
        service.create(
            changed_incident,
            proposal,
            decision,
            identity_from_headers("operator-1", "operator"),
            "stale evidence",
        )


def test_operator_can_reject_and_audit_the_proposal(tmp_path) -> None:
    incident = make_incident("inc-governance-reject")
    database, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-reject", decision)
    approval = ApprovalService(incident_repository, execution_repository, approval_repository, audit_repository).reject(
        incident,
        proposal,
        decision,
        identity_from_headers("operator-1", "operator"),
        "Reject until source owner confirms the schema change.",
    )

    assert approval.decision.value == "rejected"
    assert incident_repository.get(incident.id).status is IncidentStatus.DENIED
    assert database.connect().execute("SELECT outcome FROM audit_logs ORDER BY rowid DESC LIMIT 1").fetchone()[0] == "rejected"


def test_recovery_is_idempotent_and_validation_gates_closure(tmp_path) -> None:
    incident = make_incident()
    _, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-003", decision)
    identity = identity_from_headers("operator-1", "operator")
    ApprovalService(incident_repository, execution_repository, approval_repository, audit_repository).create(
        incident, proposal, decision, identity, "Approve recovery"
    )
    recovery = RecoveryService(incident_repository, execution_repository, approval_repository, audit_repository)

    execution = recovery.execute(incident_repository.get(incident.id), proposal, decision, identity)
    repeated = recovery.execute(incident_repository.get(incident.id), proposal, decision, identity)
    assert execution.status is RecoveryExecutionStatus.SUCCEEDED
    assert repeated.id == execution.id
    assert repeated.external_reference == execution.external_reference

    validation = ValidationService(incident_repository, audit_repository)
    result = validation.validate(incident_repository.get(incident.id), execution, identity)
    assert result.status is ValidationStatus.PASSED
    assert incident_repository.get(incident.id).status is IncidentStatus.VALIDATED


def test_missing_approval_is_blocked_and_failed_fixture_recovery_is_visible(tmp_path) -> None:
    incident = make_incident("inc-governance-004")
    _, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-004", decision)
    identity = identity_from_headers("operator-1", "operator")
    recovery = RecoveryService(incident_repository, execution_repository, approval_repository, audit_repository)

    with pytest.raises(GovernanceError, match="approval"):
        recovery.execute(incident, proposal, decision, identity)
    assert execution_repository.get_by_idempotency_key("idem-governance-004").status is RecoveryExecutionStatus.BLOCKED

    failed_incident = make_incident("inc-governance-005")
    _, failed_incident_repository, failed_execution_repository, failed_approval_repository, failed_audit_repository = repos(tmp_path / "failed", failed_incident)
    failed_decision = engine.evaluate(failed_incident, "schema_drift_recovery", ActorRole.OPERATOR)
    failed_proposal = build_execution_proposal(failed_incident, "schema_drift_recovery", "idem-governance-005", failed_decision)
    failed_identity = identity_from_headers("operator-1", "operator")
    ApprovalService(failed_incident_repository, failed_execution_repository, failed_approval_repository, failed_audit_repository).create(
        failed_incident, failed_proposal, failed_decision, failed_identity, "Approve recovery"
    )
    failed = RecoveryService(
        failed_incident_repository,
        failed_execution_repository,
        failed_approval_repository,
        failed_audit_repository,
        fixture_success=False,
    ).execute(failed_incident_repository.get(failed_incident.id), failed_proposal, failed_decision, failed_identity)
    assert failed.status is RecoveryExecutionStatus.FAILED
    assert failed_incident_repository.get(failed_incident.id).status is IncidentStatus.FAILED


def test_failed_validation_does_not_mark_incident_validated(tmp_path) -> None:
    incident = make_incident("inc-governance-006")
    _, incident_repository, execution_repository, approval_repository, audit_repository = repos(tmp_path, incident)
    engine = PolicyEngine.from_path(POLICY_PATH)
    decision = engine.evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    proposal = build_execution_proposal(incident, "schema_drift_recovery", "idem-governance-006", decision)
    identity = identity_from_headers("operator-1", "operator")
    ApprovalService(incident_repository, execution_repository, approval_repository, audit_repository).create(
        incident, proposal, decision, identity, "Approve recovery"
    )
    execution = RecoveryService(incident_repository, execution_repository, approval_repository, audit_repository).execute(
        incident_repository.get(incident.id), proposal, decision, identity
    )
    result = ValidationService(
        incident_repository,
        audit_repository,
        FixtureValidationSkill(passes=False),
    ).validate(incident_repository.get(incident.id), execution, identity)

    assert result.status is ValidationStatus.FAILED
    assert incident_repository.get(incident.id).status is IncidentStatus.RECOVERED

    with pytest.raises(GovernanceError, match="requires a succeeded recovery"):
        ValidationService(incident_repository, audit_repository).validate(
            incident_repository.get(incident.id).model_copy(update={"status": IncidentStatus.INVESTIGATED}),
            execution,
            identity,
        )
