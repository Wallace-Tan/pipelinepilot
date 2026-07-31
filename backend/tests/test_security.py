import pytest

from app.domain.contracts import ActorRole
from app.security.identity import AuthorizationError, authorize, identity_from_headers
from app.security.redaction import RedactionService


def test_identity_defaults_to_viewer_and_parses_fixture_headers() -> None:
    assert identity_from_headers(None, None).role is ActorRole.VIEWER
    identity = identity_from_headers("operator-1", "operator")
    assert identity.actor_id == "operator-1"
    assert identity.role is ActorRole.OPERATOR


def test_rbac_matrix_blocks_viewer_and_allows_operator_or_admin() -> None:
    viewer = identity_from_headers(None, None)
    operator = identity_from_headers("operator-1", "operator")
    admin = identity_from_headers("admin-1", "admin")

    with pytest.raises(AuthorizationError):
        authorize(viewer, ActorRole.OPERATOR, ActorRole.ADMIN)
    assert authorize(operator, ActorRole.OPERATOR, ActorRole.ADMIN) is operator
    assert authorize(admin, ActorRole.ADMIN) is admin


def test_invalid_role_fails_closed() -> None:
    with pytest.raises(AuthorizationError) as error:
        identity_from_headers("actor-1", "superuser")
    assert error.value.code == "invalid_actor_role"

    with pytest.raises(AuthorizationError) as missing_actor:
        identity_from_headers(None, "operator")
    assert missing_actor.value.code == "invalid_actor_id"


def test_redaction_recurses_and_preserves_metadata_without_raw_values() -> None:
    payload = {
        "contact": "owner@example.test",
        "nested": ["customer_id: CUST-9281", {"card": "4111 1111 1111 1111"}],
        "safe": False,
    }

    result = RedactionService().redact(payload)

    assert result.sanitized_payload["contact"] == "[REDACTED_EMAIL]"
    assert result.sanitized_payload["nested"][0] == "[REDACTED_IDENTIFIER]"
    assert result.sanitized_payload["nested"][1]["card"] == "[REDACTED_CARD]"
    assert result.sanitized_payload["safe"] is False
    assert result.counts == {"card": 1, "email": 1, "identifier": 1}
    assert "owner@example.test" not in repr(result.sanitized_payload)
    assert "4111" not in repr(result.sanitized_payload)
