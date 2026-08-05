from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.domain.contracts import (
    ActorRole,
    AuditEvent,
    ExecutionProposal,
    Incident,
    IncidentStatus,
    PolicyDecision,
    PolicyDecisionType,
    RecoveryExecution,
    RecoveryExecutionStatus,
    ValidationResult,
    ValidationStatus,
)
from app.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    ExecutionRepository,
    IncidentRepository,
    ValidationRepository,
)
from app.security.identity import RequestIdentity
from app.services.errors import GovernanceError
from app.services.governance import compute_request_fingerprint


class RecoveryService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        execution_repository: ExecutionRepository,
        approval_repository: ApprovalRepository,
        audit_repository: AuditRepository,
        fixture_success: bool = True,
    ) -> None:
        self.incident_repository = incident_repository
        self.execution_repository = execution_repository
        self.approval_repository = approval_repository
        self.audit_repository = audit_repository
        self.fixture_success = fixture_success

    def execute(
        self,
        incident: Incident,
        proposal: ExecutionProposal,
        policy_decision: PolicyDecision,
        identity: RequestIdentity,
    ) -> RecoveryExecution:
        self._authorize(identity)
        self._validate_proposal(incident, proposal, policy_decision)
        execution = self.execution_repository.get_by_idempotency_key(proposal.idempotency_key)
        if execution is None:
            execution = self._planned_execution(incident, proposal, policy_decision)
            self.execution_repository.save(execution)
        elif execution.request_fingerprint != proposal.request_fingerprint:
            raise GovernanceError("idempotency_conflict", "The idempotency key is bound to a different execution.")
        if execution.status in (
            RecoveryExecutionStatus.SUCCEEDED,
            RecoveryExecutionStatus.FAILED,
        ):
            return execution
        if execution.status is RecoveryExecutionStatus.BLOCKED and not (
            policy_decision.decision is PolicyDecisionType.APPROVAL_REQUIRED
            and execution.approval_id is not None
        ):
            return execution
        if policy_decision.decision is PolicyDecisionType.DENY:
            blocked = self._set_status(execution, RecoveryExecutionStatus.BLOCKED)
            self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.DENIED}))
            self._audit(incident.id, identity.role, "recovery.blocked", "policy_denied")
            self.execution_repository.save(blocked)
            raise GovernanceError("policy_denied", "The policy engine denied this execution.")
        if policy_decision.decision is PolicyDecisionType.APPROVAL_REQUIRED:
            if execution.approval_id is None:
                blocked = self._set_status(execution, RecoveryExecutionStatus.BLOCKED)
                self.execution_repository.save(blocked)
                self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.AWAITING_APPROVAL}))
                self._audit(incident.id, identity.role, "recovery.blocked", "approval_missing")
                raise GovernanceError("approval_required", "A matching approval is required before execution.")
            approval = self.approval_repository.get(execution.approval_id)
            if approval is None or approval.decision.value != "approved":
                raise GovernanceError("approval_invalid", "The recorded approval is missing or rejected.")
            if approval.request_fingerprint != proposal.request_fingerprint or approval.execution_id != proposal.id:
                raise GovernanceError("fingerprint_mismatch", "The approval does not match the proposed execution.")
        if incident.status not in (IncidentStatus.INVESTIGATED, IncidentStatus.APPROVED):
            raise GovernanceError("invalid_transition", "The incident is not ready for recovery.")
        running = self._set_status(execution, RecoveryExecutionStatus.RUNNING)
        self.execution_repository.save(running)
        self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.EXECUTING}))
        self._audit(incident.id, identity.role, "recovery.started", "fixture")
        if not self.fixture_success:
            failed = self._set_status(running, RecoveryExecutionStatus.FAILED)
            self.execution_repository.save(failed)
            self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.FAILED}))
            self._audit(incident.id, identity.role, "recovery.failed", "fixture_failure")
            return failed
        succeeded = running.model_copy(
            update={
                "status": RecoveryExecutionStatus.SUCCEEDED,
                "external_reference": f"fixture://recovery/{proposal.id}",
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self.execution_repository.save(succeeded)
        self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.RECOVERED}))
        self._audit(incident.id, identity.role, "recovery.completed", "fixture_succeeded")
        return succeeded

    @staticmethod
    def _authorize(identity: RequestIdentity) -> None:
        if identity.role not in (ActorRole.OPERATOR, ActorRole.ADMIN):
            raise GovernanceError("forbidden_role", "Only Operator or Admin can execute recovery.")

    @staticmethod
    def _validate_proposal(incident: Incident, proposal: ExecutionProposal, decision: PolicyDecision) -> None:
        if proposal.incident_id != incident.id or proposal.action != decision.action:
            raise GovernanceError("proposal_mismatch", "The execution proposal does not match the incident or policy action.")
        if proposal.policy_decision_id != decision.id or proposal.policy_version != decision.policy_version:
            raise GovernanceError("policy_mismatch", "The proposal is bound to a different policy decision.")
        if sorted(proposal.evidence_ids) != sorted(incident.evidence_ids):
            raise GovernanceError("stale_evidence", "The evidence snapshot changed after the proposal was created.")
        expected = compute_request_fingerprint(incident, proposal.action, decision, proposal.policy_version, proposal.evidence_ids)
        if expected != proposal.request_fingerprint:
            raise GovernanceError("fingerprint_mismatch", "The execution proposal fingerprint is invalid or stale.")

    @staticmethod
    def _planned_execution(incident: Incident, proposal: ExecutionProposal, decision: PolicyDecision) -> RecoveryExecution:
        now = datetime.now(timezone.utc)
        return RecoveryExecution(
            schema_version="execution.v1",
            id=proposal.id,
            incident_id=incident.id,
            action=proposal.action,
            idempotency_key=proposal.idempotency_key,
            status=RecoveryExecutionStatus.PLANNED,
            policy_decision_id=decision.id,
            approval_id=None,
            request_fingerprint=proposal.request_fingerprint,
            external_reference=None,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _set_status(execution: RecoveryExecution, status: RecoveryExecutionStatus) -> RecoveryExecution:
        return execution.model_copy(update={"status": status, "updated_at": datetime.now(timezone.utc)})

    def _audit(self, incident_id: str, role: ActorRole, action: str, outcome: str) -> None:
        self.audit_repository.append(
            AuditEvent(
                schema_version="audit_event.v1",
                id=f"audit-{uuid4().hex}",
                correlation_id=f"corr-recovery-{uuid4().hex}",
                incident_id=incident_id,
                actor_role=role,
                action=action,
                outcome=outcome,
                latency_ms=0,
                created_at=datetime.now(timezone.utc),
            )
        )


class FixtureValidationSkill:
    def __init__(self, passes: bool = True) -> None:
        self.passes = passes

    def validate(self, execution: RecoveryExecution) -> ValidationResult:
        if not self.passes:
            return ValidationResult(
                schema_version="validation_result.v1",
                execution_id=execution.id,
                incident_id=execution.incident_id,
                status=ValidationStatus.FAILED,
                mode="fixture",
                checks=["fixture staging projection check failed"],
                failure_reason="The expected post-recovery schema signal was not observed.",
            )
        return ValidationResult(
            schema_version="validation_result.v1",
            execution_id=execution.id,
            incident_id=execution.incident_id,
            status=ValidationStatus.PASSED,
            mode="fixture",
            checks=["staging projection contains order_channel", "downstream freshness restored"],
        )


class ValidationService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        audit_repository: AuditRepository,
        validation_skill: FixtureValidationSkill | None = None,
        validation_repository: ValidationRepository | None = None,
    ) -> None:
        self.incident_repository = incident_repository
        self.audit_repository = audit_repository
        self.validation_skill = validation_skill or FixtureValidationSkill()
        self.validation_repository = validation_repository

    def validate(
        self,
        incident: Incident,
        execution: RecoveryExecution,
        identity: RequestIdentity,
    ) -> ValidationResult:
        if identity.role not in (ActorRole.OPERATOR, ActorRole.ADMIN):
            raise GovernanceError("forbidden_role", "Only Operator or Admin can validate recovery.")
        if incident.status is not IncidentStatus.RECOVERED or execution.status is not RecoveryExecutionStatus.SUCCEEDED:
            raise GovernanceError("invalid_transition", "Validation requires a succeeded recovery on a recovered incident.")
        result = self.validation_skill.validate(execution)
        if self.validation_repository is not None:
            self.validation_repository.save(result)
        if result.status is ValidationStatus.PASSED:
            self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.VALIDATED}))
            outcome = "validated"
        else:
            outcome = "validation_failed"
        self.audit_repository.append(
            AuditEvent(
                schema_version="audit_event.v1",
                id=f"audit-{uuid4().hex}",
                correlation_id=f"corr-validation-{uuid4().hex}",
                incident_id=incident.id,
                execution_id=execution.id,
                actor_role=identity.role,
                action="validation.completed",
                outcome=outcome,
                latency_ms=0,
                created_at=datetime.now(timezone.utc),
            )
        )
        return result
