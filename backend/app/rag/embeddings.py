"""Embeddings multilingües (ES/EN) vía el router de modelos.

Aísla el resto del código del proveedor concreto de embeddings.
"""
from __future__ import annotations

from app.core.model_router import get_router


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await get_router().embed(texts)


async def embed_query(query: str) -> list[float]:
    return (await get_router().embed([query]))[0]
