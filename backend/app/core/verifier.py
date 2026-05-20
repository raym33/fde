"""Verifier: control de calidad antes de emitir la respuesta final.

Comprueba citas, consistencia, disclaimer legal y sobre-promesas. Devuelve un
veredicto estructurado. Si falla el parseo del JSON del modelo, se aplica una
política conservadora: no se bloquea la respuesta, pero se registra el problema.
"""
from __future__ import annotations

import json

from app.core.agents import render_prompt
from app.core.model_router import get_router
from app.core.schemas import RetrievedChunk, VerifierVerdict


async def verify(
    user_message: str,
    draft: str,
    chunks: list[RetrievedChunk],
    *,
    client_name: str,
    data_region: str,
) -> VerifierVerdict:
    system = render_prompt(
        "verifier", client_name=client_name, data_region=data_region
    )
    context = "\n\n".join(
        f"[doc:{c.document_id}#{c.chunk_id}] {c.text}" for c in chunks
    ) or "(sin contexto)"
    user = (
        f"## Petición del usuario\n{user_message}\n\n"
        f"## Contexto disponible\n{context}\n\n"
        f"## Borrador a verificar\n{draft}"
    )
    raw = await get_router().complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tier="cheap",
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(raw)
        return VerifierVerdict(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        # Fallo de parseo: no bloqueamos, pero lo dejamos anotado.
        return VerifierVerdict(
            approved=True,
            issues=[{"type": "verifier_parse_error", "detail": raw[:300]}],
            revised_answer=None,
        )
