from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def correlation_id(x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id.strip() if x_correlation_id and x_correlation_id.strip() else f"corr-api-{uuid4().hex}"


def idempotency_key(value: str | None = Header(default=None, alias="Idempotency-Key")) -> str:
    return value.strip() if value and value.strip() else f"api-{uuid4().hex}"


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
