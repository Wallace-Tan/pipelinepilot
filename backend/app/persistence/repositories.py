from __future__ import annotations

import sqlite3

from app.domain.contracts import (
    Approval,
    AuditEvent,
    Evidence,
    Feedback,
    Incident,
    PolicyDocument,
    Recommendation,
    RecoveryExecution,
    ValidationResult,
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

    def list(self, *, status: str | None = None, severity: str | None = None, pipeline: str | None = None, mode: str | None = None) -> list[Incident]:
        clauses: list[str] = []
        values: list[str] = []
        for column, value in (("status", status), ("severity", severity), ("pipeline_name", pipeline), ("mode", mode)):
            if value is not None:
                clauses.append(f"{column} = ?")
                values.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(f"SELECT id FROM incidents{where} ORDER BY detected_at DESC", values).fetchall()
        return [incident for row in rows if (incident := self.get(row["id"])) is not None]


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

    def list_for_incident(self, incident_id: str) -> list[Evidence]:
        import json
        rows = self.connection.execute("SELECT * FROM incident_evidence WHERE incident_id = ? ORDER BY collected_at", (incident_id,)).fetchall()
        return [Evidence.model_validate({
            "schema_version": row["schema_version"], "id": row["id"], "incident_id": row["incident_id"],
            "source": row["source"], "evidence_type": row["evidence_type"], "mode": row["mode"],
            "summary": row["summary"], "sanitized_payload": json.loads(row["sanitized_payload_json"]),
            "citations": json.loads(row["citations_json"]), "collected_at": row["collected_at"],
        }) for row in rows]


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

    def get_current(self) -> PolicyDocument | None:
        row = self.connection.execute("SELECT document_json FROM policies ORDER BY version DESC LIMIT 1").fetchone()
        return PolicyDocument.model_validate(__import__("json").loads(row["document_json"])) if row else None


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

    def get(self, execution_id: str) -> RecoveryExecution | None:
        row = self.connection.execute("SELECT * FROM execution_history WHERE id = ?", (execution_id,)).fetchone()
        if row is None:
            return None
        return self.get_by_idempotency_key(row["idempotency_key"])

    def list_for_incident(self, incident_id: str) -> list[RecoveryExecution]:
        rows = self.connection.execute("SELECT id FROM execution_history WHERE incident_id = ? ORDER BY created_at", (incident_id,)).fetchall()
        return [execution for row in rows if (execution := self.get(row["id"])) is not None]


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

    def list_for_incident(self, incident_id: str) -> list[Approval]:
        rows = self.connection.execute("SELECT id FROM approvals WHERE incident_id = ? ORDER BY created_at", (incident_id,)).fetchall()
        return [approval for row in rows if (approval := self.get(row["id"])) is not None]


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

    def list(self, *, incident_id: str | None = None, execution_id: str | None = None, actor_role: str | None = None, action: str | None = None, date_from: str | None = None, date_to: str | None = None) -> list[AuditEvent]:
        clauses: list[str] = []
        values: list[str] = []
        for column, value in (("incident_id", incident_id), ("execution_id", execution_id), ("actor_role", actor_role), ("action", action), ("created_at >=", date_from), ("created_at <=", date_to)):
            if value is not None:
                operator = " =" if " " not in column else " " + column.split(" ", 1)[1]
                field = column.split(" ", 1)[0]
                clauses.append(f"{field}{operator} ?")
                values.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(f"SELECT * FROM audit_logs{where} ORDER BY created_at", values).fetchall()
        return [AuditEvent.model_validate({
            "schema_version": row["schema_version"] if "schema_version" in row.keys() else "audit_event.v1",
            "id": row["id"], "correlation_id": row["correlation_id"], "incident_id": row["incident_id"],
            "execution_id": row["execution_id"], "actor_role": row["actor_role"], "action": row["action"],
            "outcome": row["outcome"], "latency_ms": row["latency_ms"], "created_at": row["created_at"],
        }) for row in rows]


class RecommendationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, recommendation: Recommendation) -> None:
        from datetime import datetime, timezone
        self.connection.execute("INSERT OR REPLACE INTO recommendations (id, incident_id, document_json, created_at) VALUES (?, ?, ?, ?)", (recommendation.id, recommendation.incident_id, recommendation.model_dump_json(), datetime.now(timezone.utc).isoformat()))
        self.connection.commit()

    def get_for_incident(self, incident_id: str) -> Recommendation | None:
        row = self.connection.execute("SELECT document_json FROM recommendations WHERE incident_id = ? ORDER BY created_at DESC LIMIT 1", (incident_id,)).fetchone()
        return Recommendation.model_validate(__import__("json").loads(row["document_json"])) if row else None


class FeedbackRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, feedback: Feedback) -> None:
        self.connection.execute("INSERT INTO feedback (id, incident_id, actor_id, correction, outcome, created_at) VALUES (?, ?, ?, ?, ?, ?)", (feedback.id, feedback.incident_id, feedback.actor_id, feedback.correction, feedback.outcome, feedback.created_at.isoformat()))
        self.connection.commit()

    def count_for_incident(self, incident_id: str) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM feedback WHERE incident_id = ?", (incident_id,)).fetchone()
        return int(row["count"])


class ValidationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, result: ValidationResult) -> None:
        from datetime import datetime, timezone
        self.connection.execute(
            "INSERT OR REPLACE INTO validation_results (execution_id, incident_id, document_json, created_at) VALUES (?, ?, ?, ?)",
            (result.execution_id, result.incident_id, result.model_dump_json(), datetime.now(timezone.utc).isoformat()),
        )
        self.connection.commit()

    def get_for_incident(self, incident_id: str) -> ValidationResult | None:
        row = self.connection.execute("SELECT document_json FROM validation_results WHERE incident_id = ? ORDER BY created_at DESC LIMIT 1", (incident_id,)).fetchone()
        return ValidationResult.model_validate(__import__("json").loads(row["document_json"])) if row else None
