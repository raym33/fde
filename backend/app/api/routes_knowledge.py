"""Contribuciones humanas al catálogo de soluciones ("human-in-the-loop data").

Permite que el equipo o expertos del cliente introduzcan novedades —nuevas
opciones, vendors, ajustes— que alimentan el motor de soluciones sin tocar el
código. Cada contribución queda auditada. Las opciones nuevas se validan contra
el schema antes de aceptarse.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.solutions import catalog
from app.core.solutions.schema import SolutionOption
from app.deps import Principal, get_principal
from app.ingest.document_parser import DocumentParseError
from app.knowledge import updates
from app.security import audit

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ContributionIn(BaseModel):
    use_case_id: str
    option: dict                 # debe validar contra SolutionOption
    note: str = ""
    scope: str = "tenant"        # "tenant" (solo este cliente) | "global"


@router.post("/solutions")
async def contribute_solution(
    body: ContributionIn,
    principal: Principal = Depends(get_principal),
) -> dict:
    # Validación de schema antes de aceptar la contribución.
    try:
        SolutionOption(**body.option)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422, detail=f"Opción inválida: {exc}"
        ) from exc

    tenant_scope = "*" if body.scope == "global" else principal.tenant_id
    catalog.add_contribution(
        use_case_id=body.use_case_id,
        option=body.option,
        author=principal.user_id,
        tenant_id=tenant_scope,
        note=body.note,
    )
    await audit.record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        action="catalog_contribution",
        detail={"use_case_id": body.use_case_id, "scope": body.scope,
                "option_id": body.option.get("id"), "note": body.note},
    )
    return {"status": "accepted", "use_case_id": body.use_case_id}


@router.get("/use-cases")
async def list_use_cases(
    principal: Principal = Depends(get_principal),
) -> dict:
    base = catalog._load_base()  # noqa: SLF001 (lectura interna intencional)
    return {
        "use_cases": [
            {"id": uc["id"], "label": uc["label"],
             "options": [o["id"] for o in uc["options"]]}
            for uc in base["use_cases"]
        ]
    }


@router.get("/updates/status")
async def knowledge_updates_status() -> dict:
    return updates.status()


@router.post("/updates")
async def upload_knowledge_update(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    source_type: str = Form(default="manual_upload"),
    scope: str = Form(default="global"),
    principal: Principal = Depends(get_principal),
) -> dict:
    if scope not in {"global", "internal"}:
        raise HTTPException(status_code=422, detail="scope debe ser 'global' o 'internal'")
    raw = await file.read()
    try:
        result = await updates.ingest_update(
            raw=raw,
            filename=file.filename or "knowledge-update",
            content_type=file.content_type,
            title=title,
            source_url=source_url,
            source_type=source_type,
            scope=scope,
            uploaded_by=principal.user_id,
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await audit.record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        action="knowledge_update_uploaded",
        detail={
            "update_id": result.update.get("id"),
            "title": result.update.get("title"),
            "filename": file.filename,
            "duplicate": result.duplicate,
            "rag_chunks": result.rag_chunks,
        },
    )
    return {
        "status": "duplicate" if result.duplicate else "accepted",
        "update": result.update,
        "brief": result.brief,
        "rag_chunks": result.rag_chunks,
    }


@router.get("/updates")
async def list_knowledge_updates(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {"updates": updates.list_updates(limit=limit)}


@router.get("/briefs")
async def list_knowledge_briefs(
    q: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    return {"briefs": updates.list_briefs(query=q, limit=limit)}


@router.get("/blocks")
async def list_knowledge_blocks(
    limit_per_block: int = Query(default=8, ge=1, le=20),
) -> dict:
    return {"blocks": updates.list_blocks(limit_per_block=limit_per_block)}
