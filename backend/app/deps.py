"""Dependencias de FastAPI: autenticación y resolución de tenant.

Cada petición se asocia a un `Principal` (tenant + usuario). El `tenant_id` es la
clave del aislamiento de datos y se propaga a RAG, store y auditoría.

- Producción: valida un JWT (Authorization: Bearer ...) firmado con `JWT_SECRET`
  y extrae `tenant_id`/`sub`.
- Desarrollo: si no hay JWT, acepta cabeceras `X-Tenant-Id` y `X-User-Id`.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.config import get_settings


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

    # Modo desarrollo: cabeceras simplificadas.
    if settings.environment != "production" and x_tenant_id:
        return Principal(
            tenant_id=x_tenant_id,
            user_id=x_user_id or "dev-user",
            client_name=x_client_name or x_tenant_id,
        )

    raise HTTPException(status_code=401, detail="Autenticación requerida")


def _decode_jwt(token: str, secret: str) -> dict:
    try:
        import jwt  # PyJWT

        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Token inválido") from exc
