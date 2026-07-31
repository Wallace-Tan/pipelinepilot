CREATE TABLE incidents (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    pipeline_name TEXT NOT NULL,
    run_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL
);

CREATE TABLE policies (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    version TEXT NOT NULL,
    mode TEXT NOT NULL,
    immutable INTEGER NOT NULL CHECK (immutable IN (0, 1)),
    document_json TEXT NOT NULL
);

CREATE TABLE incident_evidence (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    schema_version TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    summary TEXT NOT NULL,
    sanitized_payload_json TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    collected_at TEXT NOT NULL
);

CREATE TABLE execution_history (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    action TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    policy_decision_id TEXT NOT NULL,
    approval_id TEXT,
    external_reference TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    execution_id TEXT NOT NULL REFERENCES execution_history(id),
    schema_version TEXT NOT NULL,
    decision TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    incident_id TEXT REFERENCES incidents(id),
    execution_id TEXT REFERENCES execution_history(id),
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    created_at TEXT NOT NULL
);

CREATE INDEX incidents_status_idx ON incidents(status);
CREATE INDEX incidents_pipeline_run_idx ON incidents(pipeline_name, run_id);
CREATE INDEX evidence_incident_idx ON incident_evidence(incident_id);
CREATE INDEX audit_incident_idx ON audit_logs(incident_id);
CREATE INDEX audit_execution_idx ON audit_logs(execution_id);

CREATE TRIGGER audit_logs_no_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit logs are append-only');
END;

CREATE TRIGGER audit_logs_no_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit logs are append-only');
END;
