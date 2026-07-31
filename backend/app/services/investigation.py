from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from app.domain.contracts import ActorRole, AuditEvent, Incident, IncidentStatus, SafeId, StrictContract
from app.persistence.repositories import AuditRepository, EvidenceRepository, IncidentRepository
from app.security.redaction import RedactionService
from app.skills.contracts import SkillContext, SkillResult, SkillStatus
from app.skills.coordinator import SkillCoordinator


class InvestigationResult(StrictContract):
    schema_version: Literal["investigation_result.v1"]
    incident: Incident
    skill_results: list[SkillResult]
    correlation_id: SafeId

    @property
    def degraded(self) -> bool:
        return any(result.status is not SkillStatus.AVAILABLE for result in self.skill_results)

    @property
    def evidence_ids(self) -> list[str]:
        return [
            result.evidence.id
            for result in self.skill_results
            if result.evidence is not None
        ]


class InvestigationService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        evidence_repository: EvidenceRepository,
        audit_repository: AuditRepository,
        coordinator: SkillCoordinator,
        redaction_service: RedactionService,
        actor_role: ActorRole = ActorRole.OPERATOR,
    ) -> None:
        self.incident_repository = incident_repository
        self.evidence_repository = evidence_repository
        self.audit_repository = audit_repository
        self.coordinator = coordinator
        self.redaction_service = redaction_service
        self.actor_role = actor_role

    def investigate(self, incident: Incident) -> InvestigationResult:
        correlation_id = f"corr-investigation-{uuid4().hex}"
        investigating = incident.model_copy(update={"status": IncidentStatus.INVESTIGATING})
        self.incident_repository.save(investigating)
        self._audit(
            correlation_id=correlation_id,
            incident_id=incident.id,
            action="investigation.started",
            outcome="investigating",
        )

        context = SkillContext(
            schema_version="skill_context.v1",
            incident_id=incident.id,
            pipeline_name=incident.pipeline_name,
            run_id=incident.run_id,
            mode=incident.mode,
        )
        results = self.coordinator.collect(context)
        persisted_evidence_ids: list[str] = []
        for result in results:
            if result.evidence is not None:
                evidence = self._redact_evidence(result)
                self.evidence_repository.save(evidence)
                persisted_evidence_ids.append(evidence.id)
            self._audit(
                correlation_id=correlation_id,
                incident_id=incident.id,
                action=f"investigation.collect.{result.skill_name.value}",
                outcome=result.status.value,
            )

        final_evidence_ids = list(dict.fromkeys([*incident.evidence_ids, *persisted_evidence_ids]))
        investigated = investigating.model_copy(
            update={"status": IncidentStatus.INVESTIGATED, "evidence_ids": final_evidence_ids}
        )
        self.incident_repository.save(investigated)
        self._audit(
            correlation_id=correlation_id,
            incident_id=incident.id,
            action="investigation.completed",
            outcome="degraded" if any(result.status is not SkillStatus.AVAILABLE for result in results) else "investigated",
        )
        return InvestigationResult(
            schema_version="investigation_result.v1",
            incident=investigated,
            skill_results=results,
            correlation_id=correlation_id,
        )

    def _redact_evidence(self, result: SkillResult):
        assert result.evidence is not None
        redaction = self.redaction_service.redact(result.evidence.sanitized_payload)
        payload = redaction.sanitized_payload
        if not isinstance(payload, dict):
            payload = {"value": payload}
        payload = {
            **payload,
            "redaction_summary": {
                "match_count": len(redaction.matches),
                "counts": redaction.counts,
            },
        }
        return result.evidence.model_copy(update={"sanitized_payload": payload})

    def _audit(self, correlation_id: str, incident_id: str, action: str, outcome: str) -> None:
        self.audit_repository.append(
            AuditEvent(
                schema_version="audit_event.v1",
                id=f"audit-{uuid4().hex}",
                correlation_id=correlation_id,
                incident_id=incident_id,
                actor_role=self.actor_role,
                action=action,
                outcome=outcome,
                latency_ms=0,
                created_at=datetime.now(timezone.utc),
            )
        )
