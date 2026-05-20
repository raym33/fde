"""Ingestión de documentos del cliente (RAG por tenant)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import Principal, get_principal
from app.ingest.document_parser import DocumentParseError, parse_document, parser_status
from app.rag.ingest import ingest_document
from app.security import audit

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/status")
async def document_status(
    _principal: Principal = Depends(get_principal),
) -> dict:
    return parser_status()


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    ocr_if_needed: bool = Form(default=True),
    principal: Principal = Depends(get_principal),
) -> dict:
    raw = await file.read()
    try:
        extracted = parse_document(
            raw,
            filename=file.filename or "document",
            content_type=file.content_type,
            ocr_if_needed=ocr_if_needed,
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document_id = uuid.uuid4().hex
    n_chunks = await ingest_document(
        tenant_id=principal.tenant_id,
        document_id=document_id,
        text=extracted.text,
        metadata={
            "title": title or file.filename,
            "filename": file.filename,
            "content_type": file.content_type,
            "parser": extracted.parser,
            **extracted.metadata,
        },
    )

    await audit.record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        action="document_ingested",
        detail={"document_id": document_id, "chunks": n_chunks,
                "filename": file.filename, "parser": extracted.parser,
                "warnings": extracted.warnings},
    )
    return {
        "document_id": document_id,
        "chunks": n_chunks,
        "parser": extracted.parser,
        "metadata": extracted.metadata,
        "warnings": extracted.warnings,
        "text_preview": extracted.text[:600],
    }
