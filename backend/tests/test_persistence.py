import sqlite3
from datetime import datetime, timezone

import pytest

from app.domain.contracts import AuditEvent, Incident, IncidentStatus, RiskLevel, RuntimeMode
from app.persistence.database import Database
from app.persistence.repositories import AuditRepository, IncidentRepository


def incident() -> Incident:
    return Incident(
        schema_version="incident.v1",
        id="inc-test-001",
        pipeline_name="retail_orders_daily",
        run_id="run-test-001",
        mode=RuntimeMode.FIXTURE,
        status=IncidentStatus.CREATED,
        severity=RiskLevel.HIGH,
        summary="Fixture incident",
        detected_at=datetime.now(timezone.utc),
        evidence_ids=[],
    )


def audit(event_id: str) -> AuditEvent:
    return AuditEvent(
        schema_version="audit_event.v1",
        id=event_id,
        correlation_id="corr-test-001",
        incident_id="inc-test-001",
        actor_role="admin",
        action="investigate",
        outcome="started",
        latency_ms=5,
        created_at=datetime.now(timezone.utc),
    )


def test_migrations_enable_foreign_keys_and_persist_records(tmp_path) -> None:
    database = Database(tmp_path / "pipelinepilot.sqlite3")
    connection = database.connect()
    IncidentRepository(connection).save(incident())
    connection.close()

    reopened = database.connect()
    stored = IncidentRepository(reopened).get("inc-test-001")

    assert stored is not None
    assert stored.id == "inc-test-001"
    assert reopened.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert reopened.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='incidents_status_idx'").fetchone()


def test_fixture_reset_rebuilds_schema_without_replacing_database_file(tmp_path) -> None:
    database = Database(tmp_path / "pipelinepilot.sqlite3")
    connection = database.connect()
    IncidentRepository(connection).save(incident())

    reset_connection = database.reset_fixture(connection)

    assert reset_connection is connection
    assert IncidentRepository(reset_connection).get("inc-test-001") is None
    assert reset_connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert reset_connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 5


def test_audit_is_append_only_and_requires_existing_incident(tmp_path) -> None:
    connection = Database(tmp_path / "pipelinepilot.sqlite3").connect()
    IncidentRepository(connection).save(incident())
    repository = AuditRepository(connection)
    repository.append(audit("audit-test-001"))
    repository.append(audit("audit-test-002"))

    assert connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 2
    with pytest.raises(sqlite3.IntegrityError):
        repository.append(audit("audit-test-001"))

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("UPDATE audit_logs SET outcome = 'changed' WHERE id = 'audit-test-001'")

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("DELETE FROM audit_logs WHERE id = 'audit-test-001'")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("audit-test-003", "corr", "missing-incident", None, "admin", "x", "y", 1, "now"),
        )
