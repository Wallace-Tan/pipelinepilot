from __future__ import annotations

import sqlite3

from app.domain.contracts import (
    Approval,
    AuditEvent,
    Evidence,
    Incident,
    PolicyDocument,
    RecoveryExecution,
)
from app.persistence.database import json_text


class IncidentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, incident: Incident) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO incidents
            (id, schema_version, pipeline_name, run_id, mode, status, severity,
             summary, detected_at, evidence_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident.id,
                incident.schema_version,
                incident.pipeline_name,
                incident.run_id,
                incident.mode,
                incident.status,
                incident.severity,
                incident.summary,
                incident.detected_at.isoformat(),
                json_text(incident.evidence_ids),
            ),
        )
        self.connection.commit()

    def get(self, incident_id: str) -> Incident | None:
        row = self.connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if row is None:
            return None
        import json

        return Incident.model_validate(
            {
                "schema_version": row["schema_version"],
                "id": row["id"],
                "pipeline_name": row["pipeline_name"],
                "run_id": row["run_id"],
                "mode": row["mode"],
                "status": row["status"],
                "severity": row["severity"],
                "summary": row["summary"],
                "detected_at": row["detected_at"],
                "evidence_ids": json.loads(row["evidence_ids_json"]),
            }
        )


class EvidenceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, evidence: Evidence) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO incident_evidence
            (id, incident_id, schema_version, source, evidence_type, mode, summary,
             sanitized_payload_json, citations_json, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence.id,
                evidence.incident_id,
                evidence.schema_version,
                evidence.source,
                evidence.evidence_type,
                evidence.mode,
                evidence.summary,
                json_text(evidence.sanitized_payload),
                json_text([citation.model_dump(mode="json") for citation in evidence.citations]),
                evidence.collected_at.isoformat(),
            ),
        )
        self.connection.commit()


class PolicyRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, policy: PolicyDocument) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO policies
            (id, schema_version, version, mode, immutable, document_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                policy.id,
                policy.schema_version,
                policy.version,
                policy.mode,
                int(policy.immutable),
                policy.model_dump_json(),
            ),
        )
        self.connection.commit()


class ExecutionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, execution: RecoveryExecution) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO execution_history
            (id, incident_id, action, idempotency_key, status, policy_decision_id,
             approval_id, request_fingerprint, external_reference, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.id,
                execution.incident_id,
                execution.action,
                execution.idempotency_key,
                execution.status,
                execution.policy_decision_id,
                execution.approval_id,
                execution.request_fingerprint,
                execution.external_reference,
                execution.created_at.isoformat(),
                execution.updated_at.isoformat(),
            ),
        )
        self.connection.commit()

    def get_by_idempotency_key(self, idempotency_key: str) -> RecoveryExecution | None:
        row = self.connection.execute(
            "SELECT * FROM execution_history WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return RecoveryExecution.model_validate(
            {
                "schema_version": "execution.v1",
                "id": row["id"],
                "incident_id": row["incident_id"],
                "action": row["action"],
                "idempotency_key": row["idempotency_key"],
                "status": row["status"],
                "policy_decision_id": row["policy_decision_id"],
                "approval_id": row["approval_id"],
                "request_fingerprint": row["request_fingerprint"],
                "external_reference": row["external_reference"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


class ApprovalRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, approval: Approval) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO approvals
            (id, incident_id, execution_id, schema_version, decision, actor_role,
             reason, policy_version, request_fingerprint, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                approval.id,
                approval.incident_id,
                approval.execution_id,
                approval.schema_version,
                approval.decision,
                approval.actor_role,
                approval.reason,
                approval.policy_version,
                approval.request_fingerprint,
                approval.created_at.isoformat(),
            ),
        )
        self.connection.commit()

    def get(self, approval_id: str) -> Approval | None:
        row = self.connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None:
            return None
        return Approval.model_validate(
            {
                "schema_version": row["schema_version"],
                "id": row["id"],
                "incident_id": row["incident_id"],
                "execution_id": row["execution_id"],
                "decision": row["decision"],
                "actor_role": row["actor_role"],
                "reason": row["reason"],
                "policy_version": row["policy_version"],
                "request_fingerprint": row["request_fingerprint"],
                "created_at": row["created_at"],
            }
        )


class AuditRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def append(self, event: AuditEvent) -> None:
        self.connection.execute(
            """INSERT INTO audit_logs
            (id, correlation_id, incident_id, execution_id, actor_role, action,
             outcome, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.correlation_id,
                event.incident_id,
                event.execution_id,
                event.actor_role,
                event.action,
                event.outcome,
                event.latency_ms,
                event.created_at.isoformat(),
            ),
        )
        self.connection.commit()
