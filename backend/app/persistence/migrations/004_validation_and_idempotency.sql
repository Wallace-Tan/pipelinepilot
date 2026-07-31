CREATE TABLE validation_results (
    execution_id TEXT PRIMARY KEY REFERENCES execution_history(id),
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    document_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX validation_incident_idx ON validation_results(incident_id);
