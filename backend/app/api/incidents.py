from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import correlation_id, idempotency_key, require_admin, require_operator, require_viewer, resources
from app.api.schemas import (
    ActionRequest, FeedbackRequest, FeedbackResponse, IncidentCreateRequest, IncidentDetailResponse,
    IncidentListResponse, InvestigationResponse, PolicyResponse, ReportResponse,
)
from app.domain.contracts import ActorRole, AuditEvent, Feedback, Incident, IncidentStatus, PolicyDecision, PolicyDocument
from app.knowledge.services import KnowledgeRepository, RecommendationService
from app.persistence.repositories import (
    ApprovalRepository, AuditRepository, EvidenceRepository, ExecutionRepository, FeedbackRepository,
    IncidentRepository, PolicyRepository, RecommendationRepository,
)
from app.policy.engine import PolicyEngine
from app.security.identity import RequestIdentity
from app.security.redaction import RedactionService
from app.services.errors import GovernanceError
from app.services.governance import ApprovalService, build_execution_proposal
from app.services.investigation import InvestigationService
from app.services.recovery import RecoveryService, ValidationService
from app.skills.adapters import fixture_skills
from app.skills.coordinator import SkillCoordinator


router = APIRouter(prefix="/v1", tags=["incidents"])
ROOT = Path(__file__).resolve().parents[3]


def repos(request: Request):
    connection = resources(request).connection
    return (
        IncidentRepository(connection), EvidenceRepository(connection), ExecutionRepository(connection),
        ApprovalRepository(connection), AuditRepository(connection), PolicyRepository(connection),
        RecommendationRepository(connection), FeedbackRepository(connection),
    )


def recommendation_service() -> RecommendationService:
    return RecommendationService(
        ROOT / "data/fixtures/schema_drift/expected_recommendation.json",
        KnowledgeRepository(ROOT / "data/runbooks"),
    )


def error(error: GovernanceError, correlation: str):
    from fastapi import HTTPException
    code = 409 if error.code in {"invalid_transition", "idempotency_conflict", "fingerprint_mismatch", "stale_evidence", "approval_required"} else 403
    raise HTTPException(status_code=code, detail={"code": error.code, "message": error.message, "correlation_id": correlation})


@router.get("/incidents", response_model=IncidentListResponse)
def list_incidents(
    request: Request,
    identity: RequestIdentity = Depends(require_viewer),
    status: str | None = Query(default=None), severity: str | None = Query(default=None),
    pipeline: str | None = Query(default=None), mode: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
) -> IncidentListResponse:
    incident_repo, *_ = repos(request)
    items = incident_repo.list(status=status, severity=severity, pipeline=pipeline, mode=mode)
    return IncidentListResponse(items=items[offset:offset + limit], total=len(items))


@router.post("/incidents", response_model=Incident)
def create_incident(
    request: Request, body: IncidentCreateRequest, identity: RequestIdentity = Depends(require_operator),
    correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key),
) -> Incident:
    incident_repo, _, _, _, audit_repo, *_ = repos(request)
    payload = json.loads((ROOT / "data/fixtures/schema_drift/incident.json").read_text(encoding="utf-8"))
    incident = Incident.model_validate(payload)
    existing = incident_repo.get(incident.id)
    if existing:
        return existing
    incident_repo.save(incident)
    audit_repo.append(AuditEvent(schema_version="audit_event.v1", id=f"audit-{uuid4().hex}", correlation_id=correlation, incident_id=incident.id, actor_role=identity.role, action="incident.created", outcome="created", latency_ms=0, created_at=datetime.now(timezone.utc)))
    return incident


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_viewer)) -> IncidentDetailResponse:
    incident_repo, evidence_repo, execution_repo, approval_repo, audit_repo, _, recommendation_repo, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    decision = PolicyEngine.from_path(ROOT / "data/policies/demo_policy.json").evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    return IncidentDetailResponse(incident=incident, evidence=evidence_repo.list_for_incident(incident_id), recommendation=recommendation_repo.get_for_incident(incident_id), policy_decision=decision, executions=execution_repo.list_for_incident(incident_id), approvals=approval_repo.list_for_incident(incident_id), audit=audit_repo.list(incident_id=incident_id))


@router.post("/incidents/{incident_id}/investigate", response_model=InvestigationResponse)
def investigate(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)) -> InvestigationResponse:
    incident_repo, evidence_repo, _, _, audit_repo, _, recommendation_repo, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    service = InvestigationService(incident_repo, evidence_repo, audit_repo, SkillCoordinator(fixture_skills(ROOT / "data/fixtures/schema_drift")), RedactionService(), identity.role)
    result = service.investigate(incident)
    evidence = evidence_repo.list_for_incident(incident_id)
    recommendation = recommendation_service().recommend(result.incident, evidence)
    recommendation_repo.save(recommendation)
    return InvestigationResponse(incident=result.incident, evidence=evidence, recommendation=recommendation, correlation_id=result.correlation_id, degraded=result.degraded)


def action_context(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity):
    incident_repo, evidence_repo, _, _, _, _, _, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    policy = PolicyEngine.from_path(ROOT / "data/policies/demo_policy.json")
    decision = body.policy_decision or policy.evaluate(incident, body.action, identity.role)
    evidence_ids = body.evidence_ids if body.evidence_ids is not None else incident.evidence_ids
    return incident, decision, evidence_ids


@router.post("/incidents/{incident_id}/approvals")
def approve(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    incident_repo, _, execution_repo, approval_repo, audit_repo, _, _, _ = repos(request)
    incident, decision, evidence_ids = action_context(request, incident_id, body, identity)
    proposal = build_execution_proposal(incident, body.action, key, decision, evidence_ids)
    try:
        approval = ApprovalService(incident_repo, execution_repo, approval_repo, audit_repo).create(incident, proposal, decision, identity, body.reason)
    except GovernanceError as exc:
        error(exc, correlation)
    return approval


@router.post("/incidents/{incident_id}/executions")
def execute(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    incident_repo, _, execution_repo, approval_repo, audit_repo, _, _, _ = repos(request)
    incident, decision, evidence_ids = action_context(request, incident_id, body, identity)
    proposal = build_execution_proposal(incident, body.action, key, decision, evidence_ids)
    try:
        return RecoveryService(incident_repo, execution_repo, approval_repo, audit_repo).execute(incident, proposal, decision, identity)
    except GovernanceError as exc:
        error(exc, correlation)


@router.post("/incidents/{incident_id}/validate")
def validate(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    incident_repo, _, execution_repo, _, audit_repo, _, _, _ = repos(request)
    incident = incident_repo.get(incident_id)
    execution = execution_repo.list_for_incident(incident_id)[-1] if incident else None
    if incident is None or execution is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident or execution not found."})
    try:
        return ValidationService(incident_repo, audit_repo).validate(incident, execution, identity)
    except GovernanceError as exc:
        error(exc, correlation)


@router.get("/incidents/{incident_id}/report", response_model=ReportResponse)
def report(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_viewer)) -> ReportResponse:
    incident_repo, evidence_repo, _, _, audit_repo, _, recommendation_repo, feedback_repo = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    return ReportResponse(incident=incident, recommendation=recommendation_repo.get_for_incident(incident_id), evidence=evidence_repo.list_for_incident(incident_id), audit=audit_repo.list(incident_id=incident_id), feedback_count=feedback_repo.count_for_incident(incident_id))


@router.post("/incidents/{incident_id}/feedback", response_model=FeedbackResponse)
def feedback(request: Request, incident_id: str, body: FeedbackRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)) -> FeedbackResponse:
    incident_repo, _, _, _, audit_repo, _, _, feedback_repo = repos(request)
    if incident_repo.get(incident_id) is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    item = Feedback(schema_version="feedback.v1", id=f"feedback-{uuid4().hex}", incident_id=incident_id, actor_id=identity.actor_id, correction=body.correction, outcome=body.outcome, created_at=datetime.now(timezone.utc))
    feedback_repo.save(item)
    audit_repo.append(AuditEvent(schema_version="audit_event.v1", id=f"audit-{uuid4().hex}", correlation_id=correlation, incident_id=incident_id, actor_role=identity.role, action="feedback.created", outcome="recorded", latency_ms=0, created_at=datetime.now(timezone.utc)))
    return FeedbackResponse(id=item.id, incident_id=incident_id, correlation_id=correlation)


@router.get("/policies/current", response_model=PolicyResponse)
def current_policy(request: Request, identity: RequestIdentity = Depends(require_viewer)) -> PolicyResponse:
    policy = PolicyEngine.from_path(ROOT / "data/policies/demo_policy.json")
    if policy.policy is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"code": "policy_unavailable", "message": "Active policy is unavailable."})
    return PolicyResponse(policy=policy.policy)


@router.get("/audit-logs")
def audit_logs(request: Request, identity: RequestIdentity = Depends(require_admin), incident_id: str | None = None, execution_id: str | None = None, actor_role: str | None = None, action: str | None = None, date_from: str | None = None, date_to: str | None = None):
    *_, audit_repo, _, _, _ = repos(request)
    return {"items": audit_repo.list(incident_id=incident_id, execution_id=execution_id, actor_role=actor_role, action=action, date_from=date_from, date_to=date_to)}
