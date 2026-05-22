from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass

from app.config import get_settings
from app.core.db import db, init_db, utc_now


@dataclass(frozen=True)
class RuntimePolicy:
    premium_provider: str
    escalation_enabled: bool
    escalation_allow_sensitive: bool
    escalation_allowed_intents: str
    source: str = "default"


_ACTIVE_POLICY: ContextVar[RuntimePolicy | None] = ContextVar("active_runtime_policy", default=None)


def default_policy() -> RuntimePolicy:
    settings = get_settings()
    return RuntimePolicy(
        premium_provider=settings.premium_provider,
        escalation_enabled=settings.escalation_enabled,
        escalation_allow_sensitive=settings.escalation_allow_sensitive,
        escalation_allowed_intents=settings.escalation_allowed_intents,
        source="default",
    )


def current_policy() -> RuntimePolicy:
    active = _ACTIVE_POLICY.get()
    return active or default_policy()


def get_tenant_policy(tenant_id: str) -> dict:
    init_db()
    base = asdict(default_policy())
    with db() as conn:
        row = conn.execute(
            """
            SELECT tenant_id, premium_provider, escalation_enabled,
                   escalation_allow_sensitive, escalation_allowed_intents,
                   updated_at, updated_by
            FROM tenant_runtime_policies
            WHERE tenant_id = ?
            """,
            (tenant_id,),
        ).fetchone()
    if not row:
        return {
            "tenant_id": tenant_id,
            "effective": base,
            "stored": None,
        }

    stored = {
        "premium_provider": row["premium_provider"],
        "escalation_enabled": bool(row["escalation_enabled"]),
        "escalation_allow_sensitive": bool(row["escalation_allow_sensitive"]),
        "escalation_allowed_intents": row["escalation_allowed_intents"],
        "updated_at": row["updated_at"],
        "updated_by": row["updated_by"],
    }
    effective = {**base, **{k: v for k, v in stored.items() if k in base}}
    effective["source"] = "tenant_override"
    return {
        "tenant_id": tenant_id,
        "effective": effective,
        "stored": stored,
    }


def upsert_tenant_policy(
    tenant_id: str,
    *,
    updated_by: str,
    premium_provider: str,
    escalation_enabled: bool,
    escalation_allow_sensitive: bool,
    escalation_allowed_intents: str,
) -> dict:
    init_db()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO tenant_runtime_policies (
                tenant_id, premium_provider, escalation_enabled,
                escalation_allow_sensitive, escalation_allowed_intents,
                updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id) DO UPDATE SET
                premium_provider=excluded.premium_provider,
                escalation_enabled=excluded.escalation_enabled,
                escalation_allow_sensitive=excluded.escalation_allow_sensitive,
                escalation_allowed_intents=excluded.escalation_allowed_intents,
                updated_at=excluded.updated_at,
                updated_by=excluded.updated_by
            """,
            (
                tenant_id,
                premium_provider,
                1 if escalation_enabled else 0,
                1 if escalation_allow_sensitive else 0,
                escalation_allowed_intents,
                utc_now(),
                updated_by,
            ),
        )
    return get_tenant_policy(tenant_id)


def resolve_tenant_policy(tenant_id: str) -> RuntimePolicy:
    payload = get_tenant_policy(tenant_id)
    effective = payload["effective"]
    return RuntimePolicy(
        premium_provider=effective["premium_provider"],
        escalation_enabled=bool(effective["escalation_enabled"]),
        escalation_allow_sensitive=bool(effective["escalation_allow_sensitive"]),
        escalation_allowed_intents=effective["escalation_allowed_intents"],
        source=effective.get("source", "default"),
    )


@contextmanager
def activate_tenant_policy(tenant_id: str):
    policy = resolve_tenant_policy(tenant_id)
    token = _ACTIVE_POLICY.set(policy)
    try:
        yield policy
    finally:
        _ACTIVE_POLICY.reset(token)
