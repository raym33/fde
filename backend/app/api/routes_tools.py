"""Endpoints de herramientas externas conectadas al core."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import Principal, get_principal
from app.config import get_settings
from app.tools import cli_provider
from app.tools import lm_studio, web_search

router = APIRouter(prefix="/tools", tags=["tools"])


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
    settings = get_settings()
    provider = settings.premium_provider
    if provider == "lmstudio":
        return {
            "provider": provider,
            "available": True,
            "mode": "local",
            "detail": "Premium tier is configured to use LM Studio.",
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
        }
    if provider in {"claude_cli", "codex_cli"}:
        status = await cli_provider.status(provider)
        status["mode"] = "cli"
        return status
    return {
        "provider": provider,
        "available": False,
        "mode": "unknown",
        "detail": "Unsupported premium provider.",
    }
