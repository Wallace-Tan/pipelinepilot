from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import correlation_id, idempotency_key, remember_idempotent, replay_idempotent, require_admin, require_operator, require_viewer, resources
from app.api.schemas import (
    ActionRequest, ApprovalResponse, ExecutionResponse, FeedbackRequest, FeedbackResponse,
    IncidentCreateRequest, IncidentCreateResponse, IncidentDetailResponse, IncidentListResponse,
    InvestigationResponse, PolicyResponse, ReportResponse, ValidationResponse,
)
from app.config.paths import FIXTURE_ROOT, POLICY_PATH, PROJECT_ROOT, RECOMMENDATION_PATH, RUNBOOKS_ROOT
from app.decision.adapters import CocoDecisionAdapter, FixtureDecisionAdapter
from app.domain.contracts import ActorRole, AuditEvent, Feedback, Incident, IncidentStatus, PolicyDecision, PolicyDocument
from app.integrations.coco import CocoCliClient
from app.knowledge.services import KnowledgeRepository, RecommendationService
from app.persistence.repositories import (
    ApprovalRepository, AuditRepository, EvidenceRepository, ExecutionRepository, FeedbackRepository,
    IncidentRepository, PolicyRepository, RecommendationRepository, ValidationRepository,
)
from app.policy.engine import PolicyEngine
from app.security.identity import RequestIdentity
from app.security.redaction import RedactionService
from app.services.errors import GovernanceError
from app.services.governance import ApprovalService, build_execution_proposal
from app.services.investigation import InvestigationService
from app.services.recovery import RecoveryService, ValidationService
from app.skills.adapters import coco_skills, fixture_skills
from app.skills.coordinator import SkillCoordinator


router = APIRouter(prefix="/v1", tags=["incidents"])


def repos(request: Request):
    connection = resources(request).connection
    return (
        IncidentRepository(connection), EvidenceRepository(connection), ExecutionRepository(connection),
        ApprovalRepository(connection), AuditRepository(connection), PolicyRepository(connection),
        RecommendationRepository(connection), FeedbackRepository(connection), ValidationRepository(connection),
    )


def fixture_decision_adapter() -> FixtureDecisionAdapter:
    return FixtureDecisionAdapter(RecommendationService(
        RECOMMENDATION_PATH,
        KnowledgeRepository(RUNBOOKS_ROOT),
    ))


def coco_client(request: Request) -> CocoCliClient:
    settings = resources(request).settings
    return CocoCliClient(
        command=settings.coco_command,
        workdir=PROJECT_ROOT,
        connection=settings.coco_connection,
        timeout_seconds=settings.coco_timeout_seconds,
    )


def decision_adapter(request: Request):
    fallback = fixture_decision_adapter()
    if not resources(request).settings.coco_enabled:
        return fallback
    return CocoDecisionAdapter(coco_client(request), KnowledgeRepository(RUNBOOKS_ROOT), fallback)


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


@router.post("/incidents", response_model=IncidentCreateResponse)
def create_incident(
    request: Request, body: IncidentCreateRequest, identity: RequestIdentity = Depends(require_operator),
    correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key),
) -> IncidentCreateResponse:
    replay = replay_idempotent(request, key, "incident.create", body.model_dump(mode="json"), IncidentCreateResponse)
    if replay is not None:
        return replay
    incident_repo, _, _, _, audit_repo, *_ = repos(request)
    payload = json.loads((FIXTURE_ROOT / "incident.json").read_text(encoding="utf-8"))
    incident = Incident.model_validate(payload)
    existing = incident_repo.get(incident.id)
    if existing:
        response = IncidentCreateResponse(incident=existing, correlation_id=correlation)
        remember_idempotent(request, key, "incident.create", body.model_dump(mode="json"), response)
        return response
    incident_repo.save(incident)
    audit_repo.append(AuditEvent(schema_version="audit_event.v1", id=f"audit-{uuid4().hex}", correlation_id=correlation, incident_id=incident.id, actor_role=identity.role, action="incident.created", outcome="created", latency_ms=0, created_at=datetime.now(timezone.utc)))
    response = IncidentCreateResponse(incident=incident, correlation_id=correlation)
    remember_idempotent(request, key, "incident.create", body.model_dump(mode="json"), response)
    return response


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_viewer)) -> IncidentDetailResponse:
    incident_repo, evidence_repo, execution_repo, approval_repo, audit_repo, _, recommendation_repo, _, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    decision = PolicyEngine.from_path(POLICY_PATH).evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR)
    return IncidentDetailResponse(incident=incident, evidence=evidence_repo.list_for_incident(incident_id), recommendation=recommendation_repo.get_for_incident(incident_id), policy_decision=decision, executions=execution_repo.list_for_incident(incident_id), approvals=approval_repo.list_for_incident(incident_id), audit=audit_repo.list(incident_id=incident_id))


@router.post("/incidents/{incident_id}/investigate", response_model=InvestigationResponse)
def investigate(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)) -> InvestigationResponse:
    replay = replay_idempotent(request, key, "incident.investigate", {"incident_id": incident_id}, InvestigationResponse)
    if replay is not None:
        return replay
    incident_repo, evidence_repo, _, _, audit_repo, _, recommendation_repo, _, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    settings = resources(request).settings
    skills = coco_skills(coco_client(request), FIXTURE_ROOT) if settings.coco_enabled else fixture_skills(FIXTURE_ROOT)
    service = InvestigationService(incident_repo, evidence_repo, audit_repo, SkillCoordinator(skills), RedactionService(), identity.role)
    result = service.investigate(incident)
    evidence = evidence_repo.list_for_incident(incident_id)
    try:
        decision = decision_adapter(request).decide(result.incident, evidence)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"code": "decision_unavailable", "message": "A validated recommendation could not be produced from the collected evidence.", "correlation_id": correlation}) from exc
    recommendation_repo.save(decision.recommendation)
    response = InvestigationResponse(incident=result.incident, evidence=evidence, recommendation=decision.recommendation, correlation_id=correlation, degraded=result.degraded, adapter_mode=decision.adapter_mode.value, fallback_reason=decision.fallback_reason)
    remember_idempotent(request, key, "incident.investigate", {"incident_id": incident_id}, response)
    return response


def action_context(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity):
    incident_repo, evidence_repo, _, _, _, _, _, _, _ = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    policy = PolicyEngine.from_path(POLICY_PATH)
    decision = body.policy_decision or policy.evaluate(incident, body.action, identity.role)
    evidence_ids = body.evidence_ids if body.evidence_ids is not None else incident.evidence_ids
    return incident, decision, evidence_ids


@router.post("/incidents/{incident_id}/approvals", response_model=ApprovalResponse)
def approve(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    payload = {"incident_id": incident_id, **body.model_dump(mode="json")}
    replay = replay_idempotent(request, key, "incident.approval", payload, ApprovalResponse)
    if replay is not None:
        return replay
    incident_repo, _, execution_repo, approval_repo, audit_repo, _, _, _, _ = repos(request)
    incident, decision, evidence_ids = action_context(request, incident_id, body, identity)
    proposal = build_execution_proposal(incident, body.action, key, decision, evidence_ids)
    try:
        service = ApprovalService(incident_repo, execution_repo, approval_repo, audit_repo)
        approval = service.create(incident, proposal, decision, identity, body.reason) if body.approved else service.reject(incident, proposal, decision, identity, body.reason)
    except GovernanceError as exc:
        error(exc, correlation)
    response = ApprovalResponse(approval=approval, correlation_id=correlation)
    remember_idempotent(request, key, "incident.approval", payload, response)
    return response


@router.post("/incidents/{incident_id}/executions", response_model=ExecutionResponse)
def execute(request: Request, incident_id: str, body: ActionRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    payload = {"incident_id": incident_id, **body.model_dump(mode="json")}
    replay = replay_idempotent(request, key, "incident.execution", payload, ExecutionResponse)
    if replay is not None:
        return replay
    incident_repo, _, execution_repo, approval_repo, audit_repo, _, _, _, _ = repos(request)
    incident, decision, evidence_ids = action_context(request, incident_id, body, identity)
    proposal = build_execution_proposal(incident, body.action, key, decision, evidence_ids)
    try:
        execution = RecoveryService(incident_repo, execution_repo, approval_repo, audit_repo).execute(incident, proposal, decision, identity)
        response = ExecutionResponse(execution=execution, correlation_id=correlation)
        remember_idempotent(request, key, "incident.execution", payload, response)
        return response
    except GovernanceError as exc:
        error(exc, correlation)


@router.post("/incidents/{incident_id}/validate", response_model=ValidationResponse)
def validate(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    replay = replay_idempotent(request, key, "incident.validation", {"incident_id": incident_id}, ValidationResponse)
    if replay is not None:
        return replay
    incident_repo, _, execution_repo, _, audit_repo, _, _, _, validation_repo = repos(request)
    incident = incident_repo.get(incident_id)
    execution = execution_repo.list_for_incident(incident_id)[-1] if incident else None
    if incident is None or execution is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident or execution not found."})
    try:
        result = ValidationService(incident_repo, audit_repo, validation_repository=validation_repo).validate(incident, execution, identity)
        response = ValidationResponse(validation=result, correlation_id=correlation)
        remember_idempotent(request, key, "incident.validation", {"incident_id": incident_id}, response)
        return response
    except GovernanceError as exc:
        error(exc, correlation)


@router.get("/incidents/{incident_id}/report", response_model=ReportResponse)
def report(request: Request, incident_id: str, identity: RequestIdentity = Depends(require_viewer)) -> ReportResponse:
    incident_repo, evidence_repo, execution_repo, _, audit_repo, _, recommendation_repo, feedback_repo, validation_repo = repos(request)
    incident = incident_repo.get(incident_id)
    if incident is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    executions = execution_repo.list_for_incident(incident_id)
    return ReportResponse(incident=incident, recommendation=recommendation_repo.get_for_incident(incident_id), evidence=evidence_repo.list_for_incident(incident_id), policy_decision=PolicyEngine.from_path(POLICY_PATH).evaluate(incident, "schema_drift_recovery", ActorRole.OPERATOR), execution=executions[-1] if executions else None, validation=validation_repo.get_for_incident(incident_id), audit=audit_repo.list(incident_id=incident_id), feedback_count=feedback_repo.count_for_incident(incident_id))


@router.post("/incidents/{incident_id}/feedback", response_model=FeedbackResponse)
def feedback(request: Request, incident_id: str, body: FeedbackRequest, identity: RequestIdentity = Depends(require_operator), correlation: str = Depends(correlation_id), key: str = Depends(idempotency_key)) -> FeedbackResponse:
    payload = {"incident_id": incident_id, **body.model_dump(mode="json")}
    replay = replay_idempotent(request, key, "incident.feedback", payload, FeedbackResponse)
    if replay is not None:
        return replay
    incident_repo, _, _, _, audit_repo, _, _, feedback_repo, _ = repos(request)
    if incident_repo.get(incident_id) is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Incident not found."})
    item = Feedback(schema_version="feedback.v1", id=f"feedback-{uuid4().hex}", incident_id=incident_id, actor_id=identity.actor_id, correction=body.correction, outcome=body.outcome, created_at=datetime.now(timezone.utc))
    feedback_repo.save(item)
    audit_repo.append(AuditEvent(schema_version="audit_event.v1", id=f"audit-{uuid4().hex}", correlation_id=correlation, incident_id=incident_id, actor_role=identity.role, action="feedback.created", outcome="recorded", latency_ms=0, created_at=datetime.now(timezone.utc)))
    response = FeedbackResponse(id=item.id, incident_id=incident_id, correlation_id=correlation)
    remember_idempotent(request, key, "incident.feedback", payload, response)
    return response


@router.get("/policies/current", response_model=PolicyResponse)
def current_policy(request: Request, identity: RequestIdentity = Depends(require_viewer)) -> PolicyResponse:
    policy = PolicyEngine.from_path(POLICY_PATH)
    if policy.policy is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"code": "policy_unavailable", "message": "Active policy is unavailable."})
    return PolicyResponse(policy=policy.policy)


@router.get("/audit-logs")
def audit_logs(request: Request, identity: RequestIdentity = Depends(require_admin), incident_id: str | None = None, execution_id: str | None = None, actor_role: str | None = None, action: str | None = None, date_from: str | None = None, date_to: str | None = None):
    _, _, _, _, audit_repo, _, _, _, _ = repos(request)
    return {"items": audit_repo.list(incident_id=incident_id, execution_id=execution_id, actor_role=actor_role, action=action, date_from=date_from, date_to=date_to)}
