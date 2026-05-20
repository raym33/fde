"""Health y readiness."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.core.model_router import get_router
from app.ingest.document_parser import parser_status
from app.tools import lm_studio, web_search

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    model_router = get_router()
    return {
        "status": "ok",
        "demo_mode": s.demo_mode,
        "environment": s.environment,
        "data_region": s.data_region,
        "model_keys_configured": s.has_any_model_key,
        "search": web_search.status(),
        "documents": parser_status(),
        "lm_studio": await lm_studio.status(),
        "models": {
            "cheap": model_router.model_for("cheap"),
            "medium": model_router.model_for("medium"),
            "premium": model_router.model_for("premium"),
        },
    }
