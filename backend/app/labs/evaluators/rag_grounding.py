"""RAG Grounding Lab — medición REAL del retriever.

En lugar de números hardcodeados, este lab:
  1. Ingiere un *golden set* en un store aislado (tenant de laboratorio).
  2. Mide dos estrategias sobre las mismas consultas:
       - baseline = recuperación SOLO vectorial.
       - candidate = recuperación HÍBRIDA (vectorial + BM25 fusionados con RRF),
         que es la del retriever de producción.
  3. Calcula métricas de recuperación reales: recall@k, precisión de la primera
     cita (precision@1) y MRR (proxy de grounding).
  4. Comprueba el AISLAMIENTO ENTRE TENANTS de verdad: lanza las consultas del
     laboratorio contra OTRO tenant y cuenta cuántos chunks del laboratorio se
     filtran (debe ser 0).

Como la mejora se mide, el lab solo propone report si el híbrido supera al
baseline por encima del umbral. Si en el futuro mejora la rama vectorial, el
delta se reducirá automáticamente: el resultado reacciona al sistema real.
"""
from __future__ import annotations

from app.labs.base import BaseLab, run_coro, weighted_score
from app.labs.registry import register_lab
from app.labs.schemas import CoreReportDraft, LabRunResult
from app.rag import retriever as R
from app.rag.embeddings import embed_texts
from app.rag.store import InMemoryStore, StoredChunk

LAB_TENANT = "__lab_rag_grounding__"
OTHER_TENANT = "__lab_rag_other_tenant__"
TOP_K = 5

# (document_id, texto, consulta relevante)
GOLDEN: list[tuple[str, str, str]] = [
    ("doc_chatbot", "Un chatbot de soporte con RAG sobre las FAQ reduce los tickets de nivel uno.",
     "como reducir tickets de soporte con un chatbot RAG sobre FAQ"),
    ("doc_leadscoring", "El scoring predictivo de leads prioriza oportunidades comerciales usando el historico del CRM.",
     "modelo de scoring de leads con datos del CRM"),
    ("doc_rgpd", "El RGPD exige base legal y registro de actividades de tratamiento de datos personales.",
     "obligaciones del RGPD sobre registro de actividades"),
    ("doc_euaiact", "El Reglamento Europeo de IA aplica obligaciones de transparencia a partir de agosto de 2026.",
     "fechas de aplicacion del Reglamento Europeo de IA"),
    ("doc_iso42001", "ISO 42001 define un sistema de gestion de inteligencia artificial certificable.",
     "que es ISO 42001 para gestion de IA"),
    ("doc_rag", "La recuperacion hibrida combina BM25 y busqueda vectorial con fusion RRF.",
     "recuperacion hibrida BM25 y vectorial con RRF"),
    ("doc_routing", "El enrutamiento de modelos envia tareas rutinarias a modelos open source baratos.",
     "enrutamiento de modelos a open source para abaratar costes"),
    ("doc_pii", "La redaccion de PII oculta correos, IBAN y DNI antes de enviar texto a modelos externos.",
     "redaccion de PII correos IBAN DNI antes del modelo"),
    ("doc_whatsapp", "La integracion con WhatsApp Business es un canal clave de atencion en Espana.",
     "canal de atencion WhatsApp Business en Espana"),
    ("doc_ocr", "La extraccion OCR procesa PDF escaneados con tesseract cuando no hay texto embebido.",
     "OCR de PDF escaneados con tesseract"),
    ("doc_vendor", "DeepInfra y Together ofrecen inferencia de modelos open source por tokens.",
     "proveedores de inferencia open source DeepInfra Together"),
    ("doc_payback", "El payback de un proyecto de IA mide los meses para recuperar la inversion inicial.",
     "como se calcula el payback de un proyecto de IA"),
]


def _build_store() -> InMemoryStore:
    store = InMemoryStore()
    texts = [t for _, t, _ in GOLDEN]
    embeddings = run_coro(embed_texts(texts))
    chunks = [
        StoredChunk(
            chunk_id=f"{doc_id}-0",
            document_id=doc_id,
            tenant_id=LAB_TENANT,
            text=text,
            embedding=emb,
            metadata={"date": "2026-05-20"},
        )
        for (doc_id, text, _), emb in zip(GOLDEN, embeddings)
    ]
    # Documento ruido en OTRO tenant, para el test de aislamiento.
    other_emb = run_coro(embed_texts(["Documento confidencial de otro cliente distinto."]))[0]
    chunks.append(
        StoredChunk(
            chunk_id="other-0", document_id="doc_other", tenant_id=OTHER_TENANT,
            text="Documento confidencial de otro cliente distinto.", embedding=other_emb,
        )
    )
    run_coro(store.upsert(chunks))
    return store


def _vector_only(store: InMemoryStore, q_emb: list[float]) -> list[StoredChunk]:
    hits = run_coro(store.vector_search(LAB_TENANT, q_emb, TOP_K))
    return [c for c, _ in hits]


def _hybrid(store: InMemoryStore, query: str, q_emb: list[float],
            tenant_chunks: list[StoredChunk]) -> list[StoredChunk]:
    vector_hits = run_coro(store.vector_search(LAB_TENANT, q_emb, TOP_K * 3))
    vector_ranked = [c for c, _ in vector_hits]
    lexical_ranked = R._bm25_rank(query, tenant_chunks)[: TOP_K * 3]
    return R._rrf([vector_ranked, lexical_ranked])[:TOP_K]


def _metrics(results: list[tuple[str, list[StoredChunk]]]) -> dict:
    """recall@k, precision@1 (cita correcta primera) y MRR sobre el golden set."""
    n = len(results)
    recall = prec1 = mrr = 0.0
    for rel_doc, ranked in results:
        ids = [c.document_id for c in ranked]
        if rel_doc in ids:
            recall += 1.0
            rank = ids.index(rel_doc) + 1
            mrr += 1.0 / rank
            if rank == 1:
                prec1 += 1.0
    return {
        "recall_at_k": round(recall / n, 4),
        "citation_precision_at_1": round(prec1 / n, 4),
        "mrr": round(mrr / n, 4),
    }


def _score(m: dict, leakage: float) -> float:
    return weighted_score(
        {
            "recall": (m["recall_at_k"] * 100, 0.35),
            "citation": (m["citation_precision_at_1"] * 100, 0.25),
            "grounding": (m["mrr"] * 100, 0.30),
            "isolation": ((1 - leakage) * 100, 0.10),
        }
    )


@register_lab("rag_grounding")
class RagGroundingLab(BaseLab):
    def run(self) -> LabRunResult:
        store = _build_store()
        tenant_chunks = run_coro(store.all_for_tenant(LAB_TENANT))
        queries = [(rel, q) for rel, _, q in GOLDEN]
        q_embs = run_coro(embed_texts([q for _, q in queries]))

        baseline_results: list[tuple[str, list[StoredChunk]]] = []
        candidate_results: list[tuple[str, list[StoredChunk]]] = []
        leaked = 0
        total_returned_other = 0
        lab_doc_ids = {doc_id for doc_id, _, _ in GOLDEN}

        for (rel, query), q_emb in zip(queries, q_embs):
            baseline_results.append((rel, _vector_only(store, q_emb)))
            candidate_results.append((rel, _hybrid(store, query, q_emb, tenant_chunks)))
            # Test de aislamiento: misma consulta contra OTRO tenant.
            other_hits = run_coro(store.vector_search(OTHER_TENANT, q_emb, TOP_K))
            total_returned_other += len(other_hits)
            leaked += sum(1 for c, _ in other_hits if c.document_id in lab_doc_ids)

        leakage_rate = round(leaked / total_returned_other, 4) if total_returned_other else 0.0
        baseline_m = _metrics(baseline_results)
        candidate_m = _metrics(candidate_results)
        baseline_score = _score(baseline_m, leakage_rate)
        new_score = _score(candidate_m, leakage_rate)

        return LabRunResult(
            lab_id=self.definition.id,
            baseline_score=baseline_score,
            new_score=new_score,
            threshold_pct=self.definition.threshold_pct,
            metrics={
                "k": TOP_K,
                "golden_set_size": len(GOLDEN),
                "baseline": {**baseline_m, "strategy": "vector_only",
                             "tenant_leakage_rate": leakage_rate},
                "candidate": {**candidate_m, "strategy": "hybrid_bm25_vector_rrf",
                              "tenant_leakage_rate": leakage_rate},
            },
            notes=(
                "Medición real sobre golden set. baseline=vectorial puro, "
                "candidate=híbrido (BM25+vector, RRF). MRR usado como proxy de "
                "grounding hasta tener juez LLM/evals. Fuga entre tenants medida."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        cand = result.metrics["candidate"]
        base = result.metrics["baseline"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Adoptar recuperación híbrida (BM25+vector) con cita verificada",
            summary=(
                "Medido sobre un golden set: la recuperación híbrida mejora "
                "recall y precisión de la primera cita frente a la vectorial "
                "pura, manteniendo el aislamiento entre tenants."
            ),
            recommendation=(
                "Promover la recuperación híbrida a staging para los flujos de "
                "EU AI Act, GRC y motor de soluciones; añadir reranker como "
                "siguiente experimento."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "recall_at_k", "baseline": base["recall_at_k"],
                 "candidate": cand["recall_at_k"]},
                {"metric": "citation_precision_at_1", "baseline": base["citation_precision_at_1"],
                 "candidate": cand["citation_precision_at_1"]},
                {"metric": "tenant_leakage_rate", "value": cand["tenant_leakage_rate"]},
            ],
            metrics=result.metrics,
            risk_level="medium",
            rollout_plan=(
                "Activar tras feature flag para dos tenants piloto, correr evals "
                "de regresión y luego expandir a todos los tenants."
            ),
            rollback_plan="Desactivar el flag y volver a recuperación solo vectorial.",
        )
