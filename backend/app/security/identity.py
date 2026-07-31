from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.domain.contracts import ActorRole


@dataclass(frozen=True)
class RequestIdentity:
    actor_id: str
    role: ActorRole
    source: str = "fixture-header"


class AuthorizationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def identity_from_headers(actor_id: str | None, actor_role: str | None) -> RequestIdentity:
    if actor_role is None:
        return RequestIdentity(actor_id=(actor_id or "anonymous-viewer").strip(), role=ActorRole.VIEWER)
    if actor_id is None or not actor_id.strip():
        raise AuthorizationError("invalid_actor_id", "The actor identity is required for an explicit role.")
    try:
        role = ActorRole(actor_role.strip().lower())
    except ValueError as exc:
        raise AuthorizationError("invalid_actor_role", "The actor role is not recognized.") from exc
    return RequestIdentity(actor_id=actor_id.strip(), role=role)


def authorize(identity: RequestIdentity, *allowed_roles: ActorRole) -> RequestIdentity:
    if identity.role not in allowed_roles:
        allowed = ", ".join(role.value for role in allowed_roles)
        raise AuthorizationError("forbidden_role", f"This action requires one of: {allowed}.")
    return identity


def get_request_identity(
    x_actor_id: str | None = Header(default=None),
    x_actor_role: str | None = Header(default=None),
) -> RequestIdentity:
    try:
        return identity_from_headers(x_actor_id, x_actor_role)
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


def require_roles(*allowed_roles: ActorRole):
    def dependency(identity: RequestIdentity = Depends(get_request_identity)) -> RequestIdentity:
        try:
            return authorize(identity, *allowed_roles)
        except AuthorizationError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

    return dependency
