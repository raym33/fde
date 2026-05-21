"""Daily AI intelligence knowledge base.

Technicians upload TXT/MD/PDF files with fresh AI market, model, tooling or
regulatory information. We keep the raw extracted text for auditability, but
the app consumes compact briefs: summary, key points, tags and relevance notes.
That compact layer is what prevents the core CAIO prompt from drowning in long
documents.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from uuid import uuid4

from app.core.db import db, dumps, loads, utc_now
from app.core.schemas import RetrievedChunk
from app.ingest.document_parser import ExtractedDocument, parse_document
from app.rag.ingest import ingest_document


PLATFORM_KNOWLEDGE_TENANT_ID = "__platform_ai_intel__"

TAG_KEYWORDS = {
    "modelos": [
        "llm", "modelo", "model", "gemma", "qwen", "llama", "deepseek",
        "mistral", "embedding", "reranker", "open source",
    ],
    "agentes": ["agent", "agente", "workflow", "orquest", "tool", "mcp"],
    "costes": ["precio", "pricing", "coste", "cost", "token", "gpu", "tco"],
    "rag": ["rag", "retrieval", "vector", "chunk", "bm25", "pgvector"],
    "grc": [
        "eu ai act", "rgpd", "gdpr", "iso 42001", "nist", "compliance",
        "governance", "riesgo", "risk",
    ],
    "seguridad": ["security", "seguridad", "privacy", "privacidad", "pii"],
    "vendors": ["vendor", "proveedor", "api", "brave", "tavily", "perplexity"],
    "pymes": ["pyme", "sme", "empresa mediana", "500 empleados", "españa"],
}

STOPWORDS = {
    "para", "como", "with", "that", "this", "from", "into", "sobre", "entre",
    "tambien", "también", "desde", "hasta", "cada", "donde", "when", "what",
    "the", "and", "los", "las", "una", "uno", "por", "con", "del", "que",
}

FIELD_WEIGHTS = {
    "title": 4.0,
    "summary": 2.5,
    "tags": 3.0,
    "business_relevance": 2.0,
    "technical_relevance": 1.75,
    "risk_relevance": 2.25,
    "compact_text": 1.0,
}

INTENT_KEYWORDS = {
    "diagnostico": {"donde", "empezar", "primero", "priorizar", "diagnostico", "oportunidad", "quick", "win"},
    "local_cloud": {"local", "cloud", "chatgpt", "api", "ollama", "lm", "studio", "privacidad"},
    "roi": {"roi", "payback", "ahorro", "coste", "horas", "beneficio", "amortiza"},
    "roadmap": {"roadmap", "90", "dias", "implantar", "desplegar", "piloto"},
    "gobierno": {"riesgo", "gobierno", "gdpr", "rgpd", "eu", "act", "cumplimiento", "control"},
    "sector_salud": {"clinica", "clinicas", "hospital", "salud", "paciente", "historia", "medica"},
    "sector_legal": {"despacho", "despachos", "legal", "juridico", "contrato", "expediente"},
    "stack": {"stack", "n8n", "make", "chatgpt", "ollama", "herramientas", "saas"},
}

QUERY_EXPANSIONS = {
    "clinica": {"clinica", "clinicas", "salud", "sanitario", "paciente", "historia", "medica"},
    "despacho": {"despacho", "despachos", "legal", "juridico", "contrato", "expediente"},
    "asesoria": {"asesoria", "asesorias", "fiscal", "laboral", "factura", "contable"},
    "inmobiliaria": {"inmobiliaria", "inmobiliarias", "inmueble", "propiedad", "alquiler"},
    "local": {"local", "ollama", "lm", "studio", "runtime", "selfhosted", "soberania", "privacidad"},
    "cloud": {"cloud", "api", "chatgpt", "claude", "gemini", "openai", "anthropic"},
    "rag": {"rag", "retrieval", "vector", "embedding", "indice", "documental"},
    "roi": {"roi", "payback", "ahorro", "coste", "horas", "beneficio"},
    "proceso": {"proceso", "procesos", "workflow", "automatizacion", "mapear", "flujo"},
}

PHRASE_BOOSTS = {
    "local vs cloud": 8.0,
    "datos sensibles": 7.0,
    "runtime local": 6.0,
    "historia clinica": 7.0,
    "quick win": 5.0,
    "chatgpt pro": 4.0,
    "prueba local": 5.0,
    "correos repetitivos": 6.0,
}


@dataclass
class KnowledgeIngestResult:
    update: dict
    brief: dict
    rag_chunks: int
    duplicate: bool = False


@dataclass
class KnowledgeRecompactResult:
    refreshed: int
    skipped: int


def status() -> dict:
    with db() as conn:
        updates = conn.execute("SELECT COUNT(*) AS n FROM knowledge_updates").fetchone()["n"]
        briefs = conn.execute("SELECT COUNT(*) AS n FROM knowledge_briefs").fetchone()["n"]
        latest = conn.execute(
            """
            SELECT title, uploaded_at
            FROM knowledge_updates
            ORDER BY uploaded_at DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "updates": updates,
        "briefs": briefs,
        "platform_tenant_id": PLATFORM_KNOWLEDGE_TENANT_ID,
        "latest": dict(latest) if latest else None,
    }


async def ingest_update(
    *,
    raw: bytes,
    filename: str,
    content_type: str | None,
    title: str | None,
    source_url: str | None,
    source_type: str,
    scope: str,
    uploaded_by: str,
) -> KnowledgeIngestResult:
    extracted = parse_document(raw, filename=filename, content_type=content_type)
    content_hash = hashlib.sha256(extracted.text.encode("utf-8")).hexdigest()
    existing = _find_by_hash(content_hash)
    if existing:
        return KnowledgeIngestResult(
            update=existing,
            brief=get_brief_for_update(existing["id"]) or {},
            rag_chunks=0,
            duplicate=True,
        )

    update_id = uuid4().hex
    brief_id = uuid4().hex
    resolved_title = (title or _infer_title(filename, extracted.text)).strip()
    compact = compact_document(title=resolved_title, extracted=extracted, source_url=source_url)
    now = utc_now()

    with db() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_updates (
                id, content_hash, title, filename, source_url, source_type,
                scope, uploaded_by, uploaded_at, parser, raw_text, metadata_json,
                warnings_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update_id,
                content_hash,
                resolved_title,
                filename,
                source_url,
                source_type,
                scope,
                uploaded_by,
                now,
                extracted.parser,
                extracted.text,
                dumps(extracted.metadata),
                dumps(extracted.warnings),
            ),
        )
        conn.execute(
            """
            INSERT INTO knowledge_briefs (
                id, update_id, title, summary, key_points_json, tags_json,
                business_relevance, technical_relevance, risk_relevance,
                compact_text, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_id,
                update_id,
                resolved_title,
                compact["summary"],
                dumps(compact["key_points"]),
                dumps(compact["tags"]),
                compact["business_relevance"],
                compact["technical_relevance"],
                compact["risk_relevance"],
                compact["compact_text"],
                now,
            ),
        )

    rag_chunks = await ingest_document(
        tenant_id=PLATFORM_KNOWLEDGE_TENANT_ID,
        document_id=update_id,
        text=compact["compact_text"],
        metadata={
            "kind": "platform_knowledge_brief",
            "title": resolved_title,
            "source_url": source_url,
            "source_type": source_type,
            "scope": scope,
            "tags": compact["tags"],
        },
    )
    return KnowledgeIngestResult(
        update=get_update(update_id) or {},
        brief=get_brief_for_update(update_id) or {},
        rag_chunks=rag_chunks,
        duplicate=False,
    )


def compact_document(
    *,
    title: str,
    extracted: ExtractedDocument,
    source_url: str | None = None,
) -> dict:
    if _looks_like_curated_markdown(title=title, extracted=extracted):
        return _compact_curated_markdown(
            title=title,
            extracted=extracted,
            source_url=source_url,
        )

    text = _normalize(extracted.text)
    sentences = _sentences(text)
    tags = _tags(text)
    summary = _summary(sentences)
    key_points = _key_points(sentences)
    business = _relevance(
        sentences,
        ["roi", "coste", "precio", "productividad", "pyme", "cliente", "ventas", "soporte"],
        "Impacto potencial en costes, productividad, ventas o servicio al cliente para pymes.",
    )
    technical = _relevance(
        sentences,
        ["modelo", "api", "rag", "agent", "embedding", "gpu", "latency", "latencia", "benchmark"],
        "Revisar aplicabilidad técnica en routing de modelos, RAG, agentes o infraestructura.",
    )
    risk = _relevance(
        sentences,
        ["riesgo", "rgpd", "gdpr", "eu ai act", "seguridad", "privacy", "compliance", "licencia"],
        "Revisar implicaciones de seguridad, licencia, privacidad y cumplimiento antes de recomendar.",
    )
    compact_text = "\n".join(
        [
            f"Title: {title}",
            f"Source URL: {source_url or 'not provided'}",
            f"Tags: {', '.join(tags) or 'general'}",
            f"Summary: {summary}",
            "Key points:",
            *[f"- {point}" for point in key_points],
            f"Business relevance: {business}",
            f"Technical relevance: {technical}",
            f"Risk/GRC relevance: {risk}",
        ]
    )
    return {
        "summary": summary,
        "key_points": key_points,
        "tags": tags,
        "business_relevance": business,
        "technical_relevance": technical,
        "risk_relevance": risk,
        "compact_text": compact_text[:5000],
    }


def list_blocks(limit_per_block: int = 8) -> list[dict]:
    rows = list_briefs(query=None, limit=200)
    buckets: dict[str, list[dict]] = {}
    for brief in rows:
        block = _infer_block(brief["title"], brief["source_type"])
        enriched = dict(brief)
        enriched["block"] = block
        buckets.setdefault(block, []).append(enriched)

    order = ["fundamentos", "intel", "dolores", "roadmaps", "stack", "sector_publico_salud", "otros"]
    out = []
    for key in order:
        items = buckets.get(key, [])
        if not items:
            continue
        out.append(
            {
                "id": key,
                "label": _block_label(key),
                "count": len(items),
                "briefs": items[:limit_per_block],
            }
        )
    return out


def list_updates(limit: int = 50) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, filename, source_url, source_type, scope,
                   uploaded_by, uploaded_at, parser, metadata_json, warnings_json
            FROM knowledge_updates
            ORDER BY uploaded_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_update(row) for row in rows]


def recompact_all_briefs() -> KnowledgeRecompactResult:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.title, u.source_url, u.raw_text, u.parser, u.metadata_json, u.warnings_json
            FROM knowledge_updates u
            ORDER BY u.uploaded_at DESC
            """
        ).fetchall()

        refreshed = 0
        skipped = 0
        for row in rows:
            extracted = ExtractedDocument(
                text=row["raw_text"],
                parser=row["parser"],
                metadata=loads(row["metadata_json"], {}),
                warnings=loads(row["warnings_json"], []),
            )
            compact = compact_document(
                title=row["title"],
                extracted=extracted,
                source_url=row["source_url"],
            )
            updated = conn.execute(
                """
                UPDATE knowledge_briefs
                SET summary = ?, key_points_json = ?, tags_json = ?,
                    business_relevance = ?, technical_relevance = ?,
                    risk_relevance = ?, compact_text = ?, created_at = ?
                WHERE update_id = ?
                """,
                (
                    compact["summary"],
                    dumps(compact["key_points"]),
                    dumps(compact["tags"]),
                    compact["business_relevance"],
                    compact["technical_relevance"],
                    compact["risk_relevance"],
                    compact["compact_text"],
                    utc_now(),
                    row["id"],
                ),
            )
            if updated.rowcount:
                refreshed += 1
            else:
                skipped += 1
    return KnowledgeRecompactResult(refreshed=refreshed, skipped=skipped)


def list_briefs(query: str | None = None, limit: int = 10, explain: bool = False) -> list[dict]:
    if query:
        return _rank_briefs(query, limit, explain=explain)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT b.*, u.source_url, u.source_type, u.uploaded_at
            FROM knowledge_briefs b
            JOIN knowledge_updates u ON u.id = b.update_id
            ORDER BY u.uploaded_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_brief(row) for row in rows]


def retrieve_knowledge(query: str, top_k: int = 4) -> list[RetrievedChunk]:
    query_intent = _infer_query_intent(query)
    briefs = _rank_briefs(query, top_k)
    return [
        RetrievedChunk(
            chunk_id=brief["id"],
            document_id=brief["update_id"],
            text=brief["compact_text"],
            score=brief["score"],
            metadata={
                "source": "platform_knowledge",
                "title": brief["title"],
                "tags": brief["tags"],
                "source_url": brief.get("source_url"),
                "uploaded_at": brief.get("uploaded_at"),
                "block": brief.get("block"),
                "query_intent": query_intent,
            },
        )
        for brief in briefs
        if brief["score"] > 0
    ]


def get_update(update_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, title, filename, source_url, source_type, scope,
                   uploaded_by, uploaded_at, parser, metadata_json, warnings_json
            FROM knowledge_updates
            WHERE id = ?
            """,
            (update_id,),
        ).fetchone()
    return _row_to_update(row) if row else None


def get_brief_for_update(update_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            """
            SELECT b.*, u.source_url, u.source_type, u.uploaded_at
            FROM knowledge_briefs b
            JOIN knowledge_updates u ON u.id = b.update_id
            WHERE b.update_id = ?
            """,
            (update_id,),
        ).fetchone()
    return _row_to_brief(row) if row else None


def _find_by_hash(content_hash: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, title, filename, source_url, source_type, scope,
                   uploaded_by, uploaded_at, parser, metadata_json, warnings_json
            FROM knowledge_updates
            WHERE content_hash = ?
            """,
            (content_hash,),
        ).fetchone()
    return _row_to_update(row) if row else None


def _rank_briefs(query: str, limit: int, explain: bool = False) -> list[dict]:
    tokens = _tokens(query)
    expanded_tokens = _expand_query_tokens(tokens)
    folded_query = _fold(query)
    query_phrases = [phrase for phrase in PHRASE_BOOSTS if phrase in folded_query]
    broad_query = _is_broad_query(tokens)
    query_intent = _infer_query_intent(query)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT b.*, u.source_url, u.source_type, u.uploaded_at
            FROM knowledge_briefs b
            JOIN knowledge_updates u ON u.id = b.update_id
            ORDER BY u.uploaded_at DESC
            LIMIT 250
            """
        ).fetchall()
    ranked = []
    for row in rows:
        brief = _row_to_brief(row)
        field_scores = {
            field: _field_overlap_score(brief[field], expanded_tokens) * weight
            for field, weight in FIELD_WEIGHTS.items()
        }
        folded_haystack = _fold(
            " ".join(
                [
                    brief["title"],
                    brief["summary"],
                    brief["compact_text"],
                    " ".join(brief["tags"]),
                    brief["business_relevance"],
                    brief["technical_relevance"],
                    brief["risk_relevance"],
                ]
            )
        )
        phrase_score = _phrase_match_score(folded_haystack, query_phrases)
        sector_score = _sector_alignment_score(brief, expanded_tokens)
        score = float(sum(field_scores.values()))
        score += _title_phrase_boost(brief["title"], folded_query)
        score += phrase_score
        score += sector_score
        block_id = _infer_block(brief["title"], brief["source_type"])
        block_score = _block_score(block_id, broad_query, expanded_tokens)
        intent_score = _intent_score(query_intent, brief, block_id, folded_haystack)
        score += block_score
        score += intent_score
        brief["block"] = block_id
        brief["query_intent"] = query_intent
        brief["score"] = score
        if explain:
            brief["score_breakdown"] = {
                "fields": field_scores,
                "phrase": phrase_score,
                "block": block_score,
                "intent": intent_score,
                "sector": sector_score,
            }
            brief["reasons"] = _build_rank_reasons(
                query_intent=query_intent,
                block_id=block_id,
                field_scores=field_scores,
                phrase_score=phrase_score,
                block_score=block_score,
                intent_score=intent_score,
                sector_score=sector_score,
            )
        ranked.append(brief)
    ranked.sort(key=lambda item: (item["score"], item["uploaded_at"]), reverse=True)
    return ranked[:limit]


def _row_to_update(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "filename": row["filename"],
        "source_url": row["source_url"],
        "source_type": row["source_type"],
        "scope": row["scope"],
        "uploaded_by": row["uploaded_by"],
        "uploaded_at": row["uploaded_at"],
        "parser": row["parser"],
        "metadata": loads(row["metadata_json"], {}),
        "warnings": loads(row["warnings_json"], []),
    }


def _row_to_brief(row) -> dict:
    return {
        "id": row["id"],
        "update_id": row["update_id"],
        "title": row["title"],
        "summary": row["summary"],
        "key_points": loads(row["key_points_json"], []),
        "tags": loads(row["tags_json"], []),
        "business_relevance": row["business_relevance"],
        "technical_relevance": row["technical_relevance"],
        "risk_relevance": row["risk_relevance"],
        "compact_text": row["compact_text"],
        "created_at": row["created_at"],
        "source_url": row["source_url"],
        "source_type": row["source_type"],
        "uploaded_at": row["uploaded_at"],
        "score": float(row["score"]) if "score" in row.keys() else 0.0,
    }


def _infer_title(filename: str, text: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if first and len(first) <= 120:
        return first.lstrip("# ").strip()
    return filename


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _normalize_markdown_line(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"^\-\s*", "", text)
    text = re.sub(r"^\d+\.\s*", "", text)
    return text.strip("` ").strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 30]


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.-]{2,}", _fold(text))
        if token not in STOPWORDS
    ]


def _expand_query_tokens(tokens: list[str]) -> set[str]:
    expanded = set(tokens)
    for token in tokens:
        expanded.update(QUERY_EXPANSIONS.get(token, set()))
    return expanded


def _field_overlap_score(text: str | list[str], query_tokens: set[str]) -> float:
    if isinstance(text, list):
        text = " ".join(text)
    tokens = Counter(_tokens(text))
    if not tokens:
        return 0.0
    exact_hits = sum(tokens[token] for token in query_tokens)
    unique_hits = len(query_tokens & set(tokens))
    return exact_hits + (unique_hits * 0.5)


def _title_phrase_boost(title: str, folded_query: str) -> float:
    folded_title = _fold(title)
    if folded_query and folded_query in folded_title:
        return 8.0
    return 0.0


def _phrase_match_score(folded_haystack: str, phrases: list[str]) -> float:
    return sum(PHRASE_BOOSTS[phrase] for phrase in phrases if phrase in folded_haystack)


def _sector_alignment_score(brief: dict, query_tokens: set[str]) -> float:
    field_text = " ".join(
        [
            brief["title"],
            brief["summary"],
            brief["business_relevance"],
            brief["risk_relevance"],
            brief["compact_text"],
        ]
    )
    field_tokens = set(_tokens(field_text))
    score = 0.0
    sector_groups = [
        {"clinica", "salud", "sanitario", "paciente", "historia", "medica"},
        {"despacho", "legal", "juridico", "contrato", "expediente"},
        {"asesoria", "fiscal", "laboral", "contable", "factura"},
        {"inmobiliaria", "inmueble", "propiedad", "alquiler"},
    ]
    for group in sector_groups:
        if query_tokens & group and field_tokens & group:
            score += 4.0
    if {"local", "cloud"} & query_tokens and {"local", "cloud", "ollama", "lm", "studio", "api", "chatgpt"} & field_tokens:
        score += 3.5
    return score


def _is_broad_query(tokens: list[str]) -> bool:
    return any(
        token in tokens
        for token in {"donde", "donde", "empezar", "primero", "implementar", "priorizar", "mapear", "roi"}
    )


def _infer_query_intent(query: str) -> str:
    tokens = set(_tokens(query))
    scores: dict[str, float] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = float(len(tokens & keywords))
    if {"control", "permisos", "politica", "politicas", "uso", "empresa"} & tokens:
        scores["gobierno"] = scores.get("gobierno", 0.0) + 2.5
    best_intent = max(scores, key=scores.get, default="general")
    if scores.get(best_intent, 0.0) <= 0:
        return "general"
    return best_intent


def _build_rank_reasons(
    *,
    query_intent: str,
    block_id: str,
    field_scores: dict[str, float],
    phrase_score: float,
    block_score: float,
    intent_score: float,
    sector_score: float,
) -> list[str]:
    reasons: list[str] = []
    if query_intent != "general":
        reasons.append(f"Intencion detectada: {_intent_label(query_intent)}")
    if block_score > 0:
        reasons.append(f"Bloque alineado: {_block_label(block_id)}")
    if sector_score > 0:
        reasons.append("Match sectorial fuerte")
    if phrase_score > 0:
        reasons.append("Coincidencia con frase clave")
    if intent_score >= 4:
        reasons.append("Contenido muy alineado con la consulta")

    top_fields = sorted(
        ((field, score) for field, score in field_scores.items() if score > 0),
        key=lambda item: item[1],
        reverse=True,
    )[:2]
    for field, _score in top_fields:
        reasons.append(f"Match en {_field_label(field)}")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped[:5]


def _intent_score(query_intent: str, brief: dict, block_id: str, folded_haystack: str) -> float:
    if query_intent == "general":
        return 0.0

    score = 0.0
    if query_intent == "diagnostico" and block_id == "fundamentos":
        score += 4.5
    if query_intent == "local_cloud" and (
        block_id in {"fundamentos", "dolores", "stack"}
        or "local" in folded_haystack
        or "cloud" in folded_haystack
    ):
        score += 5.0
    if query_intent == "roi" and ("roi" in folded_haystack or "payback" in folded_haystack or block_id in {"fundamentos", "roadmaps"}):
        score += 4.0
    if query_intent == "roadmap" and block_id == "roadmaps":
        score += 4.5
    if query_intent == "gobierno" and ("riesgo" in folded_haystack or "cumplimiento" in folded_haystack or block_id == "dolores"):
        score += 4.25
    if query_intent == "sector_salud" and ("clinica" in folded_haystack or "salud" in folded_haystack or block_id == "sector_publico_salud"):
        score += 4.75
    if query_intent == "sector_legal" and ("despacho" in folded_haystack or "contrato" in folded_haystack or "expediente" in folded_haystack):
        score += 4.0
    if query_intent == "stack" and ("n8n" in folded_haystack or "ollama" in folded_haystack or "make" in folded_haystack or block_id == "stack"):
        score += 4.25
    return score


def _block_score(block_id: str, broad_query: bool, query_tokens: set[str]) -> float:
    if block_id == "fundamentos" and broad_query:
        return 3.0
    if block_id == "dolores" and {"riesgo", "control", "chatgpt", "cloud", "local"} & query_tokens:
        return 2.5
    if block_id == "roadmaps" and {"roadmap", "quick", "win", "implantacion"} & query_tokens:
        return 2.5
    if block_id == "sector_publico_salud" and {"clinica", "hospital", "paciente", "ayuntamiento"} & query_tokens:
        return 2.5
    return 0.0


def _tags(text: str) -> list[str]:
    low = text.lower()
    tags = [tag for tag, kws in TAG_KEYWORDS.items() if any(kw in low for kw in kws)]
    if not tags:
        common = [word for word, _ in Counter(_tokens(text)).most_common(3)]
        return common or ["general"]
    return tags


def _summary(sentences: list[str]) -> str:
    selected = sentences[:3]
    if not selected:
        return "Documento sin texto suficiente para resumen fiable."
    return " ".join(selected)[:900]


def _key_points(sentences: list[str]) -> list[str]:
    priority_terms = [
        "lanz", "nuevo", "precio", "benchmark", "mejora", "riesgo",
        "cumpl", "modelo", "agent", "rag", "api", "cost", "roi",
    ]
    scored = []
    for sentence in sentences:
        low = sentence.lower()
        score = sum(1 for term in priority_terms if term in low)
        score += min(2, len(re.findall(r"\d", sentence)))
        scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    points = [sentence for score, sentence in scored if score > 0][:6]
    if len(points) < 3:
        points.extend(sentences[: 3 - len(points)])
    return [point[:360] for point in points[:6]]


def _relevance(sentences: list[str], keywords: list[str], fallback: str) -> str:
    for sentence in sentences:
        low = sentence.lower()
        if any(keyword in low for keyword in keywords):
            return sentence[:500]
    return fallback


def _looks_like_curated_markdown(*, title: str, extracted: ExtractedDocument) -> bool:
    low_title = title.lower()
    low_text = extracted.text.lower()
    if extracted.metadata.get("format") == "text" and "#" in extracted.text:
        return True
    return (
        "inteligencia" in low_title
        or "roadmap" in low_title
        or "dolores" in low_title
        or "stack" in low_title
        or "hospitales y ayuntamientos" in low_title
        or "texto compacto" in low_text
    )


def _compact_curated_markdown(
    *,
    title: str,
    extracted: ExtractedDocument,
    source_url: str | None,
) -> dict:
    lines = [_normalize_markdown_line(line) for line in extracted.text.splitlines()]
    lines = [line for line in lines if line and len(line) > 2]
    tags = _tags(" ".join(lines))
    normalized_title = _normalize_markdown_line(title).lower()
    compact_title = re.sub(r"[\W_]+", " ", normalized_title).strip()

    paragraphs = [line for line in lines if len(line) > 40]
    summary_lines = []
    for line in paragraphs:
        low = line.lower()
        low_compact = re.sub(r"[\W_]+", " ", low).strip()
        if low == title.lower() or low_compact == compact_title or low_compact.startswith(compact_title):
            continue
        if low.startswith("naturaleza de la nota"):
            continue
        if any(low.startswith(prefix) for prefix in [
            "texto compacto para guardar",
            "fuente / cuenta",
            "fecha aproximada",
            "tema",
            "nivel de confianza",
            "requiere verificación",
        ]):
            continue
        summary_lines.append(line)
        if len(summary_lines) == 3:
            break
    summary = " ".join(summary_lines)[:900] if summary_lines else "Documento curado sin resumen legible."

    key_points: list[str] = []
    seen: set[str] = set()
    for line in lines:
        low = line.lower()
        if low == title.lower():
            continue
        if low.startswith("naturaleza de la nota"):
            continue
        if any(token in low for token in [
            "problema empresarial",
            "solucion ia",
            "quick win",
            "modulo que lo resuelve",
            "como venderlo",
            "mensaje comercial",
            "herramientas",
            "riesgos",
            "metrica",
            "implicacion",
            "oportunidad",
            "stack",
            "roadmap",
            "r.a.g",
            "rag ",
        ]) or line.endswith(":"):
            normalized = line[:280]
            if normalized not in seen:
                key_points.append(normalized)
                seen.add(normalized)
        if len(key_points) >= 6:
            break
    if not key_points:
        key_points = paragraphs[:6]

    business = _find_curated_relevance(
        lines,
        ["pyme", "hospital", "ayuntamiento", "roi", "cliente", "ciudadano", "ventas", "quick win"],
        "Revisar impacto operativo y priorizacion por quick wins o ahorro real.",
    )
    technical = _find_curated_relevance(
        lines,
        ["ollama", "lm studio", "n8n", "rag", "qdrant", "chroma", "agente", "embedding"],
        "Revisar stack tecnico, runtime local y arquitectura RAG recomendada.",
    )
    risk = _find_curated_relevance(
        lines,
        ["riesgo", "gdpr", "rgpd", "ai act", "privacidad", "alto riesgo", "trazabilidad", "supervision"],
        "Revisar implicaciones de privacidad, AI Act, supervision humana y trazabilidad.",
    )
    compact_text = "\n".join(
        [
            f"Title: {title}",
            f"Source URL: {source_url or 'not provided'}",
            f"Tags: {', '.join(tags) or 'general'}",
            f"Summary: {summary}",
            "Key points:",
            *[f"- {point}" for point in key_points[:6]],
            f"Business relevance: {business}",
            f"Technical relevance: {technical}",
            f"Risk/GRC relevance: {risk}",
        ]
    )
    return {
        "summary": summary,
        "key_points": key_points[:6],
        "tags": tags,
        "business_relevance": business,
        "technical_relevance": technical,
        "risk_relevance": risk,
        "compact_text": compact_text[:5000],
    }


def _find_curated_relevance(lines: list[str], keywords: list[str], fallback: str) -> str:
    for line in lines:
        low = line.lower()
        if any(keyword in low for keyword in keywords):
            return line[:500]
    return fallback


def _infer_block(title: str, source_type: str) -> str:
    low = f"{title} {source_type}".lower()
    if "curated_foundation" in low:
        return "fundamentos"
    if "fundamento" in low or "playbook" in low or "biblioteca" in low:
        return "fundamentos"
    if "hospital" in low or "ayuntamiento" in low or "sanidad" in low or "health" in low:
        return "sector_publico_salud"
    if "dolor" in low:
        return "dolores"
    if "roadmap" in low or "iniciativa" in low:
        return "roadmaps"
    if "stack" in low or "implementacion" in low:
        return "stack"
    if "intel" in low or "novedad" in low or "update" in low:
        return "intel"
    return "otros"


def _block_label(block_id: str) -> str:
    labels = {
        "fundamentos": "Fundamentos base",
        "intel": "Intel IA diaria",
        "dolores": "Dolores detectados",
        "roadmaps": "Roadmaps e iniciativas",
        "stack": "Stack y runtimes",
        "sector_publico_salud": "Hospitales y ayuntamientos",
        "otros": "Otros",
    }
    return labels.get(block_id, block_id)


def _intent_label(intent_id: str) -> str:
    labels = {
        "general": "general",
        "diagnostico": "diagnostico",
        "local_cloud": "local vs cloud",
        "roi": "roi",
        "roadmap": "roadmap",
        "gobierno": "gobierno y riesgo",
        "sector_salud": "sector salud",
        "sector_legal": "sector legal",
        "stack": "stack tecnico",
    }
    return labels.get(intent_id, intent_id)


def _field_label(field_id: str) -> str:
    labels = {
        "title": "titulo",
        "summary": "resumen",
        "tags": "tags",
        "business_relevance": "impacto negocio",
        "technical_relevance": "impacto tecnico",
        "risk_relevance": "riesgo y gobierno",
        "compact_text": "texto compacto",
    }
    return labels.get(field_id, field_id)
