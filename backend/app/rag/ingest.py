"""Pipeline de ingestión de documentos del cliente.

    extracción → limpieza → chunking semántico → embeddings → upsert (por tenant)

La extracción real (PDF/DOCX/OCR) se delega a Unstructured/Tika en producción;
aquí se incluye un extractor de texto plano y un chunker por longitud con solape,
suficiente para el MVP.
"""
from __future__ import annotations

import re
import uuid

from app.rag.embeddings import embed_texts
from app.rag.store import StoredChunk, get_store


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Chunking simple por caracteres con solape.

    En producción: chunking semántico (por encabezados/oraciones) con
    `unstructured`. El solape preserva contexto entre fragmentos.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


async def ingest_document(
    *,
    tenant_id: str,
    document_id: str,
    text: str,
    metadata: dict | None = None,
) -> int:
    """Ingiere un documento ya extraído a texto. Devuelve nº de chunks."""
    metadata = metadata or {}
    pieces = chunk_text(text)
    if not pieces:
        return 0
    embeddings = await embed_texts(pieces)
    stored = [
        StoredChunk(
            chunk_id=f"{document_id}-{i}-{uuid.uuid4().hex[:8]}",
            document_id=document_id,
            tenant_id=tenant_id,
            text=piece,
            embedding=emb,
            metadata={**metadata, "position": i},
        )
        for i, (piece, emb) in enumerate(zip(pieces, embeddings))
    ]
    await get_store().upsert(stored)
    return len(stored)
