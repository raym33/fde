"""Endpoints de herramientas externas conectadas al core."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.tools import lm_studio, web_search

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/web-search/status")
async def web_search_status() -> dict:
    return web_search.status()


@router.get("/web-search/test")
async def web_search_test(
    q: str = Query(default="EU AI Act Spain SME 2026"),
    max_results: int = Query(default=3, ge=1, le=10),
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
async def lm_studio_status() -> dict:
    return await lm_studio.status()


@router.get("/lm-studio/test")
async def lm_studio_test(
    prompt: str = Query(default="Responde en una frase: VirtuDirector IA listo."),
) -> dict:
    try:
        return await lm_studio.test_prompt(prompt)
    except lm_studio.LMStudioError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
