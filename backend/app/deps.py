"""FastAPI dependencies for authentication and tenant resolution.

Each request is resolved to a `Principal` (tenant + user). The `tenant_id` is
the isolation key used by RAG, persistence, and audit paths.

- Production: validates a JWT (`Authorization: Bearer ...`) signed with
  `JWT_SECRET` and extracts `tenant_id` / `sub`.
- Development: if no JWT is provided, accepts `X-Tenant-Id` and `X-User-Id`.
"""
from __future__ import annotations

from dataclasses import dataclass
import secrets

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import get_settings

basic_security = HTTPBasic()


@dataclass
class Principal:
    tenant_id: str
    user_id: str
    client_name: str


async def get_principal(
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_client_name: str | None = Header(default=None),
) -> Principal:
    settings = get_settings()

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        claims = _decode_jwt(token, settings.jwt_secret)
        return Principal(
            tenant_id=claims["tenant_id"],
            user_id=claims.get("sub", "unknown"),
            client_name=claims.get("client_name", claims["tenant_id"]),
        )

    # Development mode: simplified headers are accepted.
    if settings.environment != "production" and x_tenant_id:
        return Principal(
            tenant_id=x_tenant_id,
            user_id=x_user_id or "dev-user",
            client_name=x_client_name or x_tenant_id,
        )

    raise HTTPException(status_code=401, detail="Authentication required")


def _decode_jwt(token: str, secret: str) -> dict:
    try:
        import jwt  # PyJWT

        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def require_admin_access(
    credentials: HTTPBasicCredentials = Depends(basic_security),
) -> dict:
    settings = get_settings()
    expected_username = settings.admin_basic_username
    expected_password = settings.admin_basic_password
    valid = secrets.compare_digest(credentials.username, expected_username) and secrets.compare_digest(
        credentials.password, expected_password
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": credentials.username}
