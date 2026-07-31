from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from app.domain.contracts import Incident, PolicyDocument
from app.persistence.repositories import IncidentRepository, PolicyRepository


class FixtureSeedService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def seed(self, connection: sqlite3.Connection) -> Incident:
        incident = Incident.model_validate(json.loads((self.root / "data/fixtures/schema_drift/incident.json").read_text(encoding="utf-8")))
        IncidentRepository(connection).save(incident)
        policy = PolicyDocument.model_validate(json.loads((self.root / "data/policies/demo_policy.json").read_text(encoding="utf-8")))
        PolicyRepository(connection).save(policy)
        return incident
