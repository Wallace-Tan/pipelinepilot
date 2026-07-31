from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.contracts import (
    ActorRole, ApprovalDecision, Evidence, Incident, PolicyDecision, PolicyDocument,
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


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    evidence: list[Evidence]
    recommendation: Recommendation | None
    correlation_id: str
    degraded: bool


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident: Incident
    recommendation: Recommendation | None
    evidence: list[Evidence]
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
