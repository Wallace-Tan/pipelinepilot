import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.contracts import Evidence, Incident, IncidentStatus, PolicyDocument, Recommendation


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "schema_drift"
POLICY_PATH = REPO_ROOT / "data" / "policies" / "demo_policy.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_drift_fixtures_validate_against_contracts() -> None:
    incident = Incident.model_validate(load_json(FIXTURE_DIR / "incident.json"))
    evidence = [
        Evidence.model_validate(load_json(FIXTURE_DIR / "monitoring_status.json")),
        Evidence.model_validate(load_json(FIXTURE_DIR / "airflow_parser_log.json")),
        Evidence.model_validate(load_json(FIXTURE_DIR / "dbt_context.json")),
        Evidence.model_validate(load_json(FIXTURE_DIR / "snowflake_metadata.json")),
    ]
    recommendation = Recommendation.model_validate(load_json(FIXTURE_DIR / "expected_recommendation.json"))
    policy = PolicyDocument.model_validate(load_json(POLICY_PATH))

    assert incident.status is IncidentStatus.CREATED
    assert recommendation.evidence_ids == [item.id for item in evidence]
    assert policy.immutable is True


def test_contracts_reject_unknown_fields() -> None:
    payload = load_json(FIXTURE_DIR / "incident.json")
    payload["raw_customer_email"] = "not-allowed@example.test"

    with pytest.raises(ValidationError):
        Incident.model_validate(payload)


def test_contracts_reject_invalid_enum_values() -> None:
    payload = load_json(FIXTURE_DIR / "incident.json")
    payload["status"] = "auto_fixed"

    with pytest.raises(ValidationError):
        Incident.model_validate(payload)
