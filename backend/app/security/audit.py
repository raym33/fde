"""Log de auditoría.

Registra quién preguntó qué, qué fuentes y modelo se usaron y el veredicto del
verificador. Necesario para confianza del cliente y para defenderse si un output
es cuestionado. En producción debe ser *append-only* (tabla con hash encadenado
o WORM storage). Aquí: escritura en tabla `audit_log` y, en demo, a stdout/JSONL.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from app.config import get_settings

_AUDIT_FILE = Path(__file__).resolve().parents[2] / "audit.log.jsonl"


async def record(
    *,
    tenant_id: str,
    user_id: str,
    action: str,
    detail: dict,
) -> None:
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "detail": detail,
    }
    settings = get_settings()
    if settings.demo_mode:
        # JSONL local para inspección en desarrollo.
        with _AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return

    # Producción: insertar en tabla append-only (ver app/db/models.py).
    from app.db.session import get_session
    from app.db.models import AuditLog

    async with get_session() as session:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                detail=entry["detail"],
                ts=dt.datetime.fromisoformat(entry["ts"]),
            )
        )
        await session.commit()
