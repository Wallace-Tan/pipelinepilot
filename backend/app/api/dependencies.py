from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status

from app.config.settings import Settings
from app.domain.contracts import ActorRole
from app.persistence.database import Database
from app.security.identity import RequestIdentity, get_request_identity


@dataclass(frozen=True)
class AppResources:
    settings: Settings
    database: Database
    connection: object


def resources(request: Request) -> AppResources:
    return request.app.state.resources


def correlation_id(request: Request, x_correlation_id: str | None = Header(default=None)) -> str:
    value = x_correlation_id.strip() if x_correlation_id and x_correlation_id.strip() else f"corr-api-{uuid4().hex}"
    request.state.correlation_id = value
    return value


def idempotency_key(value: str | None = Header(default=None, alias="Idempotency-Key")) -> str:
    return value.strip() if value and value.strip() else f"api-{uuid4().hex}"


def idempotency_fingerprint(operation: str, payload: object) -> str:
    value = json.dumps({"operation": operation, "payload": payload}, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def replay_idempotent(request: Request, key: str, operation: str, payload: object, response_type):
    row = resources(request).connection.execute("SELECT fingerprint, response_json FROM api_idempotency WHERE idempotency_key = ? AND operation = ?", (key, operation)).fetchone()
    if row is None:
        return None
    if row["fingerprint"] != idempotency_fingerprint(operation, payload):
        raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": "The idempotency key was reused with a different request.", "correlation_id": getattr(request.state, "correlation_id", f"corr-api-{uuid4().hex}")})
    return response_type.model_validate_json(row["response_json"])


def remember_idempotent(request: Request, key: str, operation: str, payload: object, response) -> None:
    resources(request).connection.execute(
        "INSERT OR REPLACE INTO api_idempotency (idempotency_key, operation, fingerprint, response_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (key, operation, idempotency_fingerprint(operation, payload), response.model_dump_json(), __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()),
    )
    resources(request).connection.commit()


def require_viewer(identity: RequestIdentity = Depends(get_request_identity)) -> RequestIdentity:
    return identity


def require_operator(identity: RequestIdentity = Depends(get_request_identity)) -> RequestIdentity:
    if identity.role not in (ActorRole.OPERATOR, ActorRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "forbidden_role", "message": "Operator or Admin role required."})
    return identity


def require_admin(identity: RequestIdentity = Depends(get_request_identity)) -> RequestIdentity:
    if identity.role is not ActorRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "forbidden_role", "message": "Admin role required."})
    return identity
