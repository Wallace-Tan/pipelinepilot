from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.contracts import (
    AdapterStatus, Approval, ActorRole, Evidence, Incident, PolicyDecision, PolicyDocument,
    Recommendation, RecoveryExecution, ValidationResult,
)


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    correlation_id: str


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorBody


class IncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture: Literal["schema_drift"] = "schema_drift"


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=120)
    evidence_ids: list[str] | None = None
    policy_decision: PolicyDecision | None = None
    reason: str = Field(default="Fixture-mode operator decision.", min_length=1, max_length=500)
    approved: bool = True


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correction: str = Field(min_length=1, max_length=1000)
    outcome: str = Field(min_length=1, max_length=240)


class IncidentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Incident]
    total: int


class IncidentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    evidence: list[Evidence]
    recommendation: Recommendation | None
    policy_decision: PolicyDecision | None
    executions: list[RecoveryExecution]
    approvals: list[Any]
    audit: list[Any]


class IncidentCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    correlation_id: str


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    evidence: list[Evidence]
    recommendation: Recommendation | None
    correlation_id: str
    degraded: bool
    adapter_mode: str
    adapter_status: dict[str, AdapterStatus]
    fallback_reason: str | None = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval: Approval
    correlation_id: str


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution: RecoveryExecution
    correlation_id: str


class ValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation: ValidationResult
    correlation_id: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    recommendation: Recommendation | None
    evidence: list[Evidence]
    policy_decision: PolicyDecision | None
    execution: RecoveryExecution | None
    validation: ValidationResult | None
    audit: list[Any]
    feedback_count: int


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    incident_id: str
    correlation_id: str


class PolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy: PolicyDocument


class DemoStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["demo_status.v1"]
    mode: str
    fixture: Literal["schema_drift"]
    incident_id: str
    database_ready: bool
    adapters: dict[str, str]
    adapter_status: dict[str, AdapterStatus]


class DemoResetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["demo_reset.v1"]
    incident_id: str
    mode: str
    fixture: Literal["schema_drift"]
    reset_at: datetime
    correlation_id: str
