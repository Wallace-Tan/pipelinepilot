from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from app.config.paths import FIXTURE_ROOT, POLICY_PATH, PROJECT_ROOT
from app.domain.contracts import Incident, PolicyDocument
from app.persistence.repositories import IncidentRepository, PolicyRepository


class FixtureSeedService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def seed(self, connection: sqlite3.Connection) -> Incident:
        incident_path = self.root / FIXTURE_ROOT.relative_to(PROJECT_ROOT) / "incident.json"
        policy_path = self.root / POLICY_PATH.relative_to(PROJECT_ROOT)
        incident = Incident.model_validate(json.loads(incident_path.read_text(encoding="utf-8")))
        incident_repository = IncidentRepository(connection)
        incident_repository.save(incident)
        queue_path = self.root / FIXTURE_ROOT.relative_to(PROJECT_ROOT) / "incidents"
        for additional_path in sorted(queue_path.glob("*.json")):
            incident_repository.save(Incident.model_validate(json.loads(additional_path.read_text(encoding="utf-8"))))
        policy = PolicyDocument.model_validate(json.loads(policy_path.read_text(encoding="utf-8")))
        PolicyRepository(connection).save(policy)
        return incident
