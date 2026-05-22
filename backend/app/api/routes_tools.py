"""Endpoints de herramientas externas conectadas al core."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import Principal, get_principal
from app.config import get_settings
from app.core import runtime_policy
from app.core.schemas import RetrievedChunk
from app.security import sensitivity
from app.tools import cli_provider
from app.tools import lm_studio, web_search

router = APIRouter(prefix="/tools", tags=["tools"])


class RuntimePolicyRequest(BaseModel):
    premium_provider: Literal["lmstudio", "anthropic_api", "openai_api", "claude_cli", "codex_cli"]
    escalation_enabled: bool
    escalation_allow_sensitive: bool = False
    escalation_allowed_intents: str = "strategy,grc,solution,opportunity,deliverable"


class SensitivityAnalyzeRequest(BaseModel):
    text: str
    context_chunks: list[str] = []


@router.get("/web-search/status")
async def web_search_status(
    _principal: Principal = Depends(get_principal),
) -> dict:
    return web_search.status()


@router.get("/web-search/test")
async def web_search_test(
    q: str = Query(default="EU AI Act Spain SME 2026"),
    max_results: int = Query(default=3, ge=1, le=10),
    _principal: Principal = Depends(get_principal),
) -> dict:
    try:
        results = await web_search.search(q, max_results=max_results)
        return {"status": web_search.status(), "results": [r.model_dump() for r in results]}
    except web_search.WebSearchAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except web_search.WebSearchRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except web_search.WebSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/lm-studio/status")
async def lm_studio_status(
    _principal: Principal = Depends(get_principal),
) -> dict:
    return await lm_studio.status()


@router.get("/lm-studio/test")
async def lm_studio_test(
    prompt: str = Query(default="Responde en una frase: VirtuDirector IA listo."),
    _principal: Principal = Depends(get_principal),
) -> dict:
    try:
        return await lm_studio.test_prompt(prompt)
    except lm_studio.LMStudioError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/premium/status")
async def premium_status(
    _principal: Principal = Depends(get_principal),
) -> dict:
    policy = runtime_policy.resolve_tenant_policy(_principal.tenant_id)
    settings = get_settings()
    provider = policy.premium_provider
    if provider == "lmstudio":
        return {
            "provider": provider,
            "available": True,
            "mode": "local",
            "detail": "Premium tier is configured to use LM Studio.",
            "policy_source": policy.source,
        }
    if provider in {"anthropic_api", "openai_api"}:
        key_present = bool(
            settings.anthropic_api_key if provider == "anthropic_api" else settings.openai_api_key
        )
        return {
            "provider": provider,
            "available": key_present,
            "mode": "api",
            "detail": "API key detected." if key_present else "API key missing.",
            "policy_source": policy.source,
        }
    if provider in {"claude_cli", "codex_cli"}:
        status = await cli_provider.status(provider)
        status["mode"] = "cli"
        status["policy_source"] = policy.source
        return status
    return {
        "provider": provider,
        "available": False,
        "mode": "unknown",
        "detail": "Unsupported premium provider.",
        "policy_source": policy.source,
    }


@router.get("/runtime-policy")
async def runtime_policy_status(
    principal: Principal = Depends(get_principal),
) -> dict:
    return runtime_policy.get_tenant_policy(principal.tenant_id)


@router.post("/runtime-policy")
async def runtime_policy_update(
    body: RuntimePolicyRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    return runtime_policy.upsert_tenant_policy(
        principal.tenant_id,
        updated_by=principal.user_id,
        premium_provider=body.premium_provider,
        escalation_enabled=body.escalation_enabled,
        escalation_allow_sensitive=body.escalation_allow_sensitive,
        escalation_allowed_intents=body.escalation_allowed_intents,
    )


@router.post("/sensitivity/analyze")
async def analyze_sensitivity(
    body: SensitivityAnalyzeRequest,
    _principal: Principal = Depends(get_principal),
) -> dict:
    chunks = [
        RetrievedChunk(
            chunk_id=f"ctx-{index}",
            document_id=f"context-{index}",
            text=text,
            score=1.0,
            metadata={},
        )
        for index, text in enumerate(body.context_chunks, start=1)
    ]
    assessment = sensitivity.classify_sensitivity(body.text, chunks)
    return {
        "level": assessment.level,
        "labels": assessment.labels,
        "reasons": assessment.reasons,
        "pii_placeholders": assessment.pii_placeholders,
    }
