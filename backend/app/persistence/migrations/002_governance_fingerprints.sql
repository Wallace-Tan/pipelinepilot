ALTER TABLE execution_history ADD COLUMN request_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE approvals ADD COLUMN request_fingerprint TEXT NOT NULL DEFAULT '';

CREATE INDEX execution_fingerprint_idx ON execution_history(request_fingerprint);
CREATE INDEX approval_fingerprint_idx ON approvals(request_fingerprint);
