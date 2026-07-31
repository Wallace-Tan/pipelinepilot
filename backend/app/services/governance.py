from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.contracts import (
    ActorRole,
    Approval,
    ApprovalDecision,
    AuditEvent,
    ExecutionProposal,
    Incident,
    IncidentStatus,
    PolicyDecision,
    PolicyDecisionType,
    RecoveryExecution,
    RecoveryExecutionStatus,
)
from app.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    ExecutionRepository,
    IncidentRepository,
)
from app.policy.engine import ROLE_RANK
from app.security.identity import RequestIdentity
from app.services.errors import GovernanceError


def compute_request_fingerprint(
    incident: Incident,
    action: str,
    policy_decision: PolicyDecision,
    policy_version: str,
    evidence_ids: list[str],
) -> str:
    snapshot = {
        "incident_id": incident.id,
        "pipeline_name": incident.pipeline_name,
        "run_id": incident.run_id,
        "mode": incident.mode.value,
        "severity": incident.severity.value,
        "action": action,
        "policy_decision_id": policy_decision.id,
        "policy_version": policy_version,
        "evidence_ids": sorted(evidence_ids),
    }
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return f"fp-{digest}"


def build_execution_proposal(
    incident: Incident,
    action: str,
    idempotency_key: str,
    policy_decision: PolicyDecision,
    evidence_ids: list[str] | None = None,
) -> ExecutionProposal:
    selected_evidence_ids = list(evidence_ids if evidence_ids is not None else incident.evidence_ids)
    proposal_id = "execution-proposal-" + "".join(character if character.isalnum() or character in "_.:-" else "-" for character in idempotency_key)
    return ExecutionProposal(
        schema_version="execution_proposal.v1",
        id=proposal_id,
        incident_id=incident.id,
        action=action,
        idempotency_key=idempotency_key,
        policy_decision_id=policy_decision.id,
        policy_version=policy_decision.policy_version,
        evidence_ids=selected_evidence_ids,
        request_fingerprint=compute_request_fingerprint(
            incident,
            action,
            policy_decision,
            policy_decision.policy_version,
            selected_evidence_ids,
        ),
    )


class ApprovalService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        execution_repository: ExecutionRepository,
        approval_repository: ApprovalRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self.incident_repository = incident_repository
        self.execution_repository = execution_repository
        self.approval_repository = approval_repository
        self.audit_repository = audit_repository

    def create(
        self,
        incident: Incident,
        proposal: ExecutionProposal,
        policy_decision: PolicyDecision,
        identity: RequestIdentity,
        reason: str,
    ) -> Approval:
        self._validate_request(incident, proposal, policy_decision, identity)
        execution = self._ensure_planned_execution(incident, proposal, policy_decision)
        if execution.approval_id is not None:
            raise GovernanceError("approval_exists", "This execution proposal already has an approval.")
        now = datetime.now(timezone.utc)
        approval = Approval(
            schema_version="approval.v1",
            id=f"approval-{uuid4().hex}",
            incident_id=incident.id,
            execution_id=proposal.id,
            decision=ApprovalDecision.APPROVED,
            actor_role=identity.role,
            reason=reason,
            policy_version=proposal.policy_version,
            request_fingerprint=proposal.request_fingerprint,
            created_at=now,
        )
        self.approval_repository.save(approval)
        self.execution_repository.save(execution.model_copy(update={"approval_id": approval.id}))
        self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.APPROVED}))
        self._audit(incident.id, identity.role, "policy.evaluated", policy_decision.decision.value)
        self._audit(incident.id, identity.role, "approval.created", approval.decision.value)
        return approval

    def reject(
        self,
        incident: Incident,
        proposal: ExecutionProposal,
        policy_decision: PolicyDecision,
        identity: RequestIdentity,
        reason: str,
    ) -> Approval:
        self._validate_request(incident, proposal, policy_decision, identity)
        execution = self._ensure_planned_execution(incident, proposal, policy_decision)
        if execution.approval_id is not None:
            raise GovernanceError("approval_exists", "This execution proposal already has an approval.")
        approval = Approval(
            schema_version="approval.v1",
            id=f"approval-{uuid4().hex}",
            incident_id=incident.id,
            execution_id=proposal.id,
            decision=ApprovalDecision.REJECTED,
            actor_role=identity.role,
            reason=reason,
            policy_version=proposal.policy_version,
            request_fingerprint=proposal.request_fingerprint,
            created_at=datetime.now(timezone.utc),
        )
        self.approval_repository.save(approval)
        self.incident_repository.save(incident.model_copy(update={"status": IncidentStatus.DENIED}))
        self._audit(incident.id, identity.role, "approval.rejected", approval.decision.value)
        return approval

    def _validate_request(
        self,
        incident: Incident,
        proposal: ExecutionProposal,
        policy_decision: PolicyDecision,
        identity: RequestIdentity,
    ) -> None:
        if identity.role not in (ActorRole.OPERATOR, ActorRole.ADMIN):
            raise GovernanceError("forbidden_role", "Only Operator or Admin can approve an execution.")
        if policy_decision.decision is not PolicyDecisionType.APPROVAL_REQUIRED:
            raise GovernanceError("approval_not_required", "Approval is only valid for approval-required policy decisions.")
        if proposal.incident_id != incident.id or proposal.action != policy_decision.action:
            raise GovernanceError("proposal_mismatch", "The execution proposal does not match the incident or policy action.")
        if proposal.policy_decision_id != policy_decision.id or proposal.policy_version != policy_decision.policy_version:
            raise GovernanceError("policy_mismatch", "The proposal is bound to a different policy decision.")
        if sorted(proposal.evidence_ids) != sorted(incident.evidence_ids):
            raise GovernanceError("stale_evidence", "The evidence snapshot changed after the proposal was created.")
        expected = compute_request_fingerprint(
            incident,
            proposal.action,
            policy_decision,
            proposal.policy_version,
            proposal.evidence_ids,
        )
        if expected != proposal.request_fingerprint:
            raise GovernanceError("fingerprint_mismatch", "The execution proposal fingerprint is invalid or stale.")
        if incident.status not in (IncidentStatus.INVESTIGATED, IncidentStatus.AWAITING_APPROVAL):
            raise GovernanceError("invalid_transition", "The incident is not ready for approval.")
        if policy_decision.required_approver_role and ROLE_RANK[identity.role] < ROLE_RANK[policy_decision.required_approver_role]:
            raise GovernanceError("forbidden_role", "The actor does not meet the policy approver requirement.")

    def _ensure_planned_execution(
        self,
        incident: Incident,
        proposal: ExecutionProposal,
        policy_decision: PolicyDecision,
    ) -> RecoveryExecution:
        existing = self.execution_repository.get_by_idempotency_key(proposal.idempotency_key)
        if existing is not None:
            if existing.request_fingerprint != proposal.request_fingerprint:
                raise GovernanceError("idempotency_conflict", "The idempotency key is bound to a different execution.")
            return existing
        now = datetime.now(timezone.utc)
        execution = RecoveryExecution(
            schema_version="execution.v1",
            id=proposal.id,
            incident_id=incident.id,
            action=proposal.action,
            idempotency_key=proposal.idempotency_key,
            status=RecoveryExecutionStatus.PLANNED,
            policy_decision_id=policy_decision.id,
            approval_id=None,
            request_fingerprint=proposal.request_fingerprint,
            external_reference=None,
            created_at=now,
            updated_at=now,
        )
        self.execution_repository.save(execution)
        return execution

    def _audit(self, incident_id: str, role: ActorRole, action: str, outcome: str) -> None:
        self.audit_repository.append(
            AuditEvent(
                schema_version="audit_event.v1",
                id=f"audit-{uuid4().hex}",
                correlation_id=f"corr-governance-{uuid4().hex}",
                incident_id=incident_id,
                actor_role=role,
                action=action,
                outcome=outcome,
                latency_ms=0,
                created_at=datetime.now(timezone.utc),
            )
        )
