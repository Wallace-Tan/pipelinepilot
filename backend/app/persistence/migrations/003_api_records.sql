CREATE TABLE recommendations (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    document_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    actor_id TEXT NOT NULL,
    correction TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX recommendations_incident_idx ON recommendations(incident_id);
CREATE INDEX feedback_incident_idx ON feedback(incident_id);
