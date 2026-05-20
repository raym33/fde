"""Recuperación híbrida: vectorial + léxica (BM25), fusionadas con RRF.

Solo vectorial pierde precisión en nombres propios, cifras y siglas; BM25 lo
compensa. Tras la fusión, en producción se aplica un *reranker* (cross-encoder)
sobre el top-k antes de pasar al LLM (marcado como TODO).

Todo filtrado por `tenant_id` — el aislamiento lo garantiza el store.
"""
from __future__ import annotations

from app.rag.embeddings import embed_query
from app.rag.store import StoredChunk, get_store
from app.core.schemas import RetrievedChunk

RRF_K = 60  # constante estándar de Reciprocal Rank Fusion


def _bm25_rank(query: str, chunks: list[StoredChunk]) -> list[StoredChunk]:
    """Ranking léxico. Usa rank_bm25 si está; si no, solape de tokens."""
    if not chunks:
        return []
    corpus = [c.text.lower().split() for c in chunks]
    q = query.lower().split()
    try:
        from rank_bm25 import BM25Okapi

        scores = BM25Okapi(corpus).get_scores(q)
    except Exception:
        qset = set(q)
        scores = [len(qset & set(doc)) for doc in corpus]
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    return [chunks[i] for i in order]


def _rrf(rankings: list[list[StoredChunk]]) -> list[StoredChunk]:
    """Fusión por Reciprocal Rank Fusion de varias listas ordenadas."""
    scores: dict[str, float] = {}
    by_id: dict[str, StoredChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking):
            by_id[chunk.chunk_id] = chunk
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (
                RRF_K + rank + 1
            )
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [by_id[cid] for cid in ordered]


async def retrieve(query: str, tenant_id: str, top_k: int = 8) -> list[RetrievedChunk]:
    store = get_store()

    # Rama vectorial
    q_emb = await embed_query(query)
    vector_hits = await store.vector_search(tenant_id, q_emb, top_k * 3)
    vector_ranked = [c for c, _ in vector_hits]

    # Rama léxica (BM25) sobre el universo del tenant
    tenant_chunks = await store.all_for_tenant(tenant_id)
    lexical_ranked = _bm25_rank(query, tenant_chunks)[: top_k * 3]

    # Fusión
    fused = _rrf([vector_ranked, lexical_ranked])[:top_k]

    # TODO(producción): rerank con cross-encoder (p. ej. bge-reranker) aquí,
    # antes de devolver, para maximizar precisión del top-k.

    scores = {c.chunk_id: s for c, s in vector_hits}
    return [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            text=c.text,
            score=scores.get(c.chunk_id, 0.0),
            metadata=c.metadata,
        )
        for c in fused
    ]
