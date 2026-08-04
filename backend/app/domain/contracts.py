from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


SafeId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=96, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$"),
]


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimeMode(StrEnum):
    FIXTURE = "fixture"
    SANDBOX = "sandbox"
    LIVE = "live"


class ActorRole(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class IncidentStatus(StrEnum):
    CREATED = "created"
    INVESTIGATING = "investigating"
    INVESTIGATED = "investigated"
    AWAITING_APPROVAL = "awaiting approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    RECOVERED = "recovered"
    VALIDATED = "validated"
    REPORTED = "reported"
    FAILED = "failed"
    DENIED = "denied"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PolicyDecisionType(StrEnum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


class EvidenceSource(StrEnum):
    MONITORING = "monitoring"
    AIRFLOW_LOG = "airflow_log"
    DBT = "dbt"
    SNOWFLAKE_METADATA = "snowflake_metadata"
    KNOWLEDGE = "knowledge"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class RecoveryExecutionStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class EvidenceCitation(StrictContract):
    document_id: SafeId
    title: str = Field(min_length=1, max_length=160)
    section: str = Field(min_length=1, max_length=160)


class Incident(StrictContract):
    schema_version: Literal["incident.v1"]
    id: SafeId
    pipeline_name: str = Field(min_length=1, max_length=120)
    run_id: SafeId
    mode: RuntimeMode
    status: IncidentStatus
    severity: RiskLevel
    summary: str = Field(min_length=1, max_length=500)
    detected_at: datetime
    evidence_ids: list[SafeId] = Field(default_factory=list)


class Evidence(StrictContract):
    schema_version: Literal["evidence.v1"]
    id: SafeId
    incident_id: SafeId
    source: EvidenceSource
    evidence_type: str = Field(min_length=1, max_length=80)
    mode: RuntimeMode
    summary: str = Field(min_length=1, max_length=700)
    sanitized_payload: dict[str, Any]
    citations: list[EvidenceCitation] = Field(default_factory=list)
    collected_at: datetime


class AdapterStatus(StrictContract):
    mode: str = Field(min_length=1, max_length=40)
    status: str = Field(min_length=1, max_length=40)
    source: str = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, max_length=500)


class Recommendation(StrictContract):
    schema_version: Literal["recommendation.v1"]
    id: SafeId
    incident_id: SafeId
    cause: str = Field(min_length=1, max_length=500)
    confidence_band: ConfidenceBand
    evidence_ids: list[SafeId] = Field(min_length=1)
    runbook_ids: list[SafeId] = Field(min_length=1)
    recommended_action: str = Field(min_length=1, max_length=240)
    uncertainty: str = Field(min_length=1, max_length=500)
    mode: RuntimeMode


class PolicyRule(StrictContract):
    id: SafeId
    action: str = Field(min_length=1, max_length=120)
    environment: RuntimeMode
    minimum_role: ActorRole
    risk: RiskLevel
    decision: PolicyDecisionType
    required_approver_role: ActorRole | None = None
    minimum_severity: RiskLevel | None = None
    max_retry_count: int | None = Field(default=None, ge=0)
    reasons: list[str] = Field(min_length=1)


class PolicyDocument(StrictContract):
    schema_version: Literal["policy.v1"]
    id: SafeId
    version: str = Field(min_length=1, max_length=40)
    mode: RuntimeMode
    immutable: bool
    rules: list[PolicyRule] = Field(min_length=1)
    default_decision: PolicyDecisionType = PolicyDecisionType.DENY


class PolicyDecision(StrictContract):
    schema_version: Literal["policy_decision.v1"]
    id: SafeId
    policy_version: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=120)
    decision: PolicyDecisionType
    risk: RiskLevel
    matched_rule_id: SafeId | None = None
    required_approver_role: ActorRole | None = None
    reasons: list[str] = Field(min_length=1)


class Approval(StrictContract):
    schema_version: Literal["approval.v1"]
    id: SafeId
    incident_id: SafeId
    execution_id: SafeId
    decision: ApprovalDecision
    actor_role: ActorRole
    reason: str = Field(min_length=1, max_length=500)
    policy_version: str = Field(min_length=1, max_length=40)
    request_fingerprint: SafeId
    created_at: datetime


class ExecutionProposal(StrictContract):
    schema_version: Literal["execution_proposal.v1"]
    id: SafeId
    incident_id: SafeId
    action: str = Field(min_length=1, max_length=120)
    idempotency_key: SafeId
    policy_decision_id: SafeId
    policy_version: str = Field(min_length=1, max_length=40)
    evidence_ids: list[SafeId] = Field(default_factory=list)
    request_fingerprint: SafeId


class RecoveryExecution(StrictContract):
    schema_version: Literal["execution.v1"]
    id: SafeId
    incident_id: SafeId
    action: str = Field(min_length=1, max_length=120)
    idempotency_key: SafeId
    status: RecoveryExecutionStatus
    policy_decision_id: SafeId
    approval_id: SafeId | None = None
    request_fingerprint: SafeId
    external_reference: str | None = Field(default=None, max_length=160)
    created_at: datetime
    updated_at: datetime


class ValidationResult(StrictContract):
    schema_version: Literal["validation_result.v1"]
    execution_id: SafeId
    incident_id: SafeId
    status: ValidationStatus
    mode: RuntimeMode
    checks: list[str] = Field(min_length=1)
    failure_reason: str | None = Field(default=None, max_length=500)


class Feedback(StrictContract):
    schema_version: Literal["feedback.v1"]
    id: SafeId
    incident_id: SafeId
    actor_id: SafeId
    correction: str = Field(min_length=1, max_length=1000)
    outcome: str = Field(min_length=1, max_length=240)
    created_at: datetime


class AuditEvent(StrictContract):
    schema_version: Literal["audit_event.v1"]
    id: SafeId
    correlation_id: SafeId
    incident_id: SafeId | None = None
    execution_id: SafeId | None = None
    actor_role: ActorRole
    action: str = Field(min_length=1, max_length=120)
    outcome: str = Field(min_length=1, max_length=120)
    latency_ms: int = Field(ge=0)
    created_at: datetime
