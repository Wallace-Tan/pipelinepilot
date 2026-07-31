import json
from datetime import datetime
from pathlib import Path

from app.domain.contracts import Incident, IncidentStatus
from app.persistence.database import Database
from app.persistence.repositories import AuditRepository, EvidenceRepository, IncidentRepository
from app.security.redaction import RedactionService
from app.services.investigation import InvestigationService
from app.skills.adapters import FixtureMonitoringSkill, fixture_skills
from app.skills.coordinator import SkillCoordinator


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "data" / "fixtures" / "schema_drift"


def load_incident() -> Incident:
    return Incident.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))


def service(tmp_path, skills=None) -> tuple[InvestigationService, Database]:
    database = Database(tmp_path / "pipelinepilot.sqlite3")
    connection = database.connect()
    return (
        InvestigationService(
            incident_repository=IncidentRepository(connection),
            evidence_repository=EvidenceRepository(connection),
            audit_repository=AuditRepository(connection),
            coordinator=SkillCoordinator(skills or fixture_skills(FIXTURES)),
            redaction_service=RedactionService(),
        ),
        database,
    )


def test_investigation_persists_evidence_audit_and_final_status(tmp_path) -> None:
    investigation, database = service(tmp_path)

    result = investigation.investigate(load_incident())
    connection = database.connect()

    assert result.incident.status is IncidentStatus.INVESTIGATED
    assert len(result.evidence_ids) == 4
    assert connection.execute("SELECT COUNT(*) FROM incident_evidence").fetchone()[0] == 4
    assert connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 6
    assert connection.execute("SELECT status FROM incidents").fetchone()[0] == "investigated"
    evidence_payload = json.loads(connection.execute("SELECT sanitized_payload_json FROM incident_evidence LIMIT 1").fetchone()[0])
    assert evidence_payload["redaction_summary"]["match_count"] == 0


def test_investigation_preserves_partial_unavailable_skill(tmp_path) -> None:
    skills = fixture_skills(FIXTURES)
    skills[0] = FixtureMonitoringSkill(tmp_path / "missing-monitoring.json")
    investigation, database = service(tmp_path, skills)

    result = investigation.investigate(load_incident())
    connection = database.connect()

    assert result.incident.status is IncidentStatus.INVESTIGATED
    assert result.degraded is True
    assert any(item.degradation_reason == "fixture not found: missing-monitoring.json" for item in result.skill_results)
    assert connection.execute("SELECT COUNT(*) FROM incident_evidence").fetchone()[0] == 3
    assert connection.execute("SELECT COUNT(*) FROM audit_logs WHERE outcome = 'unavailable'").fetchone()[0] == 1
