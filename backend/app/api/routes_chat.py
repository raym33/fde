"""Endpoint de chat con streaming SSE.

Orquesta la respuesta y emite eventos Server-Sent Events al frontend. Cada
petición queda registrada en auditoría (con tenant + usuario).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.orchestrator import run_stream
from app.core.schemas import ChatRequest
from app.deps import Principal, get_principal
from app.security import audit, pii

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    body: ChatRequest,
    principal: Principal = Depends(get_principal),
) -> StreamingResponse:
    # Redacción de PII antes de cualquier procesamiento con modelos externos.
    safe_message, _pii_map = pii.redact(body.message)

    await audit.record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        action="chat_request",
        detail={
            "conversation_id": body.conversation_id,
            "message_preview": safe_message[:200],
        },
    )

    async def event_source():
        verified = None
        intent = None
        try:
            async for chunk in run_stream(
                safe_message,
                principal.tenant_id,
                client_name=principal.client_name,
            ):
                if chunk.type == "final":
                    verified = chunk.meta.get("verified")
                    intent = chunk.meta.get("intent")
                yield _sse(chunk.model_dump())
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "data": str(exc), "meta": {}})
        finally:
            await audit.record(
                tenant_id=principal.tenant_id,
                user_id=principal.user_id,
                action="chat_response",
                detail={"intent": intent, "verified": verified},
            )

    return StreamingResponse(event_source(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
