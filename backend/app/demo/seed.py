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
        IncidentRepository(connection).save(incident)
        policy = PolicyDocument.model_validate(json.loads(policy_path.read_text(encoding="utf-8")))
        PolicyRepository(connection).save(policy)
        return incident
