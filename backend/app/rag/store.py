"""Almacén vectorial multi-tenant.

AISLAMIENTO POR TENANT (crítico de seguridad): toda lectura y escritura filtra
por `tenant_id`. La búsqueda vectorial incluye el filtro de tenant en la propia
query, nunca en post-proceso, para que sea imposible mezclar datos de clientes.

Dos backends:
  - pgvector (producción): `PgVectorStore`. Una colección lógica por tenant vía
    columna `tenant_id` + índice; opcionalmente esquema/colección dedicada.
  - en memoria (DEMO_MODE / tests): `InMemoryStore`.

`get_store()` elige según configuración.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.config import get_settings


@dataclass
class StoredChunk:
    chunk_id: str
    document_id: str
    tenant_id: str
    text: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class InMemoryStore:
    """Backend de desarrollo. NO usar en producción."""

    def __init__(self) -> None:
        self._chunks: list[StoredChunk] = []

    async def upsert(self, chunks: list[StoredChunk]) -> None:
        ids = {c.chunk_id for c in chunks}
        self._chunks = [c for c in self._chunks if c.chunk_id not in ids]
        self._chunks.extend(chunks)

    async def vector_search(
        self, tenant_id: str, query_embedding: list[float], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        # Filtro por tenant ANTES de puntuar: aislamiento estricto.
        scoped = [c for c in self._chunks if c.tenant_id == tenant_id]
        scored = [(c, cosine(query_embedding, c.embedding)) for c in scoped]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def all_for_tenant(self, tenant_id: str) -> list[StoredChunk]:
        return [c for c in self._chunks if c.tenant_id == tenant_id]


class PgVectorStore:
    """Backend de producción sobre Postgres + pgvector.

    Esquema esperado (ver `app/db/models.py`):
        chunks(chunk_id PK, document_id, tenant_id, text, embedding vector,
               metadata jsonb)
    con índice ivfflat/hnsw sobre `embedding` y un índice btree sobre
    `tenant_id`. La query usa `WHERE tenant_id = :tenant` para el aislamiento.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        # La conexión real (psycopg + pgvector) se inicializa perezosamente.
        self._pool = None

    async def _ensure_pool(self):
        if self._pool is None:
            # import perezoso para no requerir psycopg en demo
            import psycopg_pool

            self._pool = psycopg_pool.AsyncConnectionPool(self.database_url)
        return self._pool

    async def upsert(self, chunks: list[StoredChunk]) -> None:
        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            for c in chunks:
                await conn.execute(
                    """
                    INSERT INTO chunks
                        (chunk_id, document_id, tenant_id, text, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata
                    """,
                    (c.chunk_id, c.document_id, c.tenant_id, c.text,
                     c.embedding, _json(c.metadata)),
                )

    async def vector_search(
        self, tenant_id: str, query_embedding: list[float], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT chunk_id, document_id, tenant_id, text, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM chunks
                WHERE tenant_id = %s            -- aislamiento por tenant
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, tenant_id, query_embedding, top_k),
            )
            rows = await cur.fetchall()
        out: list[tuple[StoredChunk, float]] = []
        for r in rows:
            out.append(
                (
                    StoredChunk(
                        chunk_id=r[0], document_id=r[1], tenant_id=r[2],
                        text=r[3], embedding=[], metadata=r[4] or {},
                    ),
                    float(r[5]),
                )
            )
        return out

    async def all_for_tenant(self, tenant_id: str) -> list[StoredChunk]:
        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            cur = await conn.execute(
                "SELECT chunk_id, document_id, tenant_id, text, metadata "
                "FROM chunks WHERE tenant_id = %s",
                (tenant_id,),
            )
            rows = await cur.fetchall()
        return [
            StoredChunk(
                chunk_id=r[0], document_id=r[1], tenant_id=r[2],
                text=r[3], embedding=[], metadata=r[4] or {},
            )
            for r in rows
        ]


def _json(d: dict) -> str:
    import json

    return json.dumps(d)


_store = None


def get_store():
    global _store
    if _store is None:
        settings = get_settings()
        if settings.demo_mode:
            _store = InMemoryStore()
        else:
            _store = PgVectorStore(settings.database_url)
    return _store
