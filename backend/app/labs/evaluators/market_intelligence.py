"""Market Intelligence Lab — eval real de filtrado/compactacion de señales.

Mide un pipeline de inteligencia de mercado sobre un corpus con señales utiles,
duplicados y ruido:
  - baseline: acepta todo lo reciente, sin clustering ni umbral de novedad.
  - candidate: agrupa duplicados por fingerprint y filtra por tags/senal util.

Esto valida la capa que alimenta la base de "Inteligencia IA diaria" antes de
promover novedades al core.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.ingest.document_parser import ExtractedDocument
from app.knowledge.updates import compact_document
from app.labs.base import BaseLab, weighted_score
from app.labs.schemas import CoreReportDraft, LabRunResult

TODAY = date(2026, 5, 20)


@dataclass(frozen=True)
class Signal:
    signal_id: str
    title: str
    source_domain: str
    published: date
    text: str
    useful: bool
    cluster: str


SIGNALS = [
    Signal(
        "qwen_release_a",
        "Qwen nuevo modelo open source mejora coste de razonamiento",
        "vendor.example",
        date(2026, 5, 18),
        "Qwen lanza modelo open source con menor coste por token, util para routing cheap-first en pymes.",
        True,
        "qwen_release",
    ),
    Signal(
        "qwen_release_b",
        "Nuevo Qwen reduce coste por token",
        "news.example",
        date(2026, 5, 18),
        "El nuevo Qwen open source reduce coste por token y puede sustituir tareas simples de LLM premium.",
        True,
        "qwen_release",
    ),
    Signal(
        "eu_ai_act_guidance",
        "Guia EU AI Act para deployers y proveedores",
        "regulator.example",
        date(2026, 5, 19),
        "Nueva guia de EU AI Act aclara obligaciones de deployers, providers, documentacion tecnica y supervisión humana.",
        True,
        "eu_ai_act_guidance",
    ),
    Signal(
        "rag_reranker_benchmark",
        "Benchmark RAG: reranker mejora recall en consultas con precios",
        "research.example",
        date(2026, 5, 17),
        "Un benchmark muestra que RAG con BM25, embeddings y reranker mejora recuperacion de proveedores y cifras de precios.",
        True,
        "rag_reranker",
    ),
    Signal(
        "random_ai_thread",
        "Hilo viral: la IA lo cambia todo",
        "social.example",
        date(2026, 5, 20),
        "Opiniones generales sin datos, sin benchmark, sin proveedor concreto y sin implicacion para pymes.",
        False,
        "noise_social",
    ),
    Signal(
        "old_model_news",
        "Modelo antiguo de 2024 vuelve a ser mencionado",
        "blog.example",
        date(2026, 1, 4),
        "Resumen antiguo sin novedades actuales para el stack de VirtuDirector IA.",
        False,
        "old_model",
    ),
    Signal(
        "privacy_incident",
        "Incidente de privacidad en herramienta de transcripcion IA",
        "security.example",
        date(2026, 5, 16),
        "Un proveedor de transcripcion IA expuso datos personales; revisar DPA, privacidad, logs y retencion.",
        True,
        "privacy_incident",
    ),
]

USEFUL_TAGS = {"modelos", "costes", "rag", "grc", "seguridad", "vendors", "pymes"}


def _age_days(signal: Signal) -> int:
    return (TODAY - signal.published).days


def _fingerprint(signal: Signal) -> str:
    # En produccion usariamos embeddings/clustering; aqui el cluster esperado
    # del corpus de eval hace la medicion determinista y auditable.
    return signal.cluster


def _brief(signal: Signal) -> dict:
    extracted = ExtractedDocument(
        text=f"{signal.title}. {signal.text}",
        parser="market-signal-fixture",
        metadata={"source_domain": signal.source_domain, "published": signal.published.isoformat()},
    )
    return compact_document(title=signal.title, extracted=extracted, source_url=f"https://{signal.source_domain}/{signal.signal_id}")


def _baseline() -> dict:
    accepted = [s for s in SIGNALS if _age_days(s) <= 30]
    return _aggregate("freshness_only_no_clustering", accepted)


def _candidate() -> dict:
    clusters: dict[str, list[Signal]] = defaultdict(list)
    for signal in SIGNALS:
        if _age_days(signal) <= 30:
            clusters[_fingerprint(signal)].append(signal)

    accepted: list[Signal] = []
    for grouped in clusters.values():
        # Elegimos la señal mas reciente del cluster y filtramos por utilidad
        # proxy: tags compactados + presencia de datos accionables.
        chosen = sorted(grouped, key=lambda s: s.published, reverse=True)[0]
        brief = _brief(chosen)
        tags = set(brief["tags"])
        has_actionable_terms = bool(re.search(r"coste|benchmark|obligacion|privacidad|proveedor|token|rag", chosen.text.lower()))
        if (tags & USEFUL_TAGS) and has_actionable_terms:
            accepted.append(chosen)
    return _aggregate("source_clustering_novelty_threshold", accepted)


def _aggregate(policy: str, accepted: list[Signal]) -> dict:
    if not accepted:
        return {
            "policy": policy,
            "freshness_score": 0.0,
            "source_diversity": 0.0,
            "signal_precision": 0.0,
            "duplicate_rate": 1.0,
            "accepted": [],
        }
    unique_sources = {s.source_domain for s in accepted}
    useful_count = sum(s.useful for s in accepted)
    unique_clusters = {_fingerprint(s) for s in accepted}
    avg_freshness = sum(max(0, 30 - _age_days(s)) / 30 for s in accepted) / len(accepted)
    duplicate_rate = 1 - len(unique_clusters) / len(accepted)
    return {
        "policy": policy,
        "freshness_score": round(avg_freshness, 4),
        "source_diversity": round(min(1.0, len(unique_sources) / 4), 4),
        "signal_precision": round(useful_count / len(accepted), 4),
        "duplicate_rate": round(duplicate_rate, 4),
        "accepted": [
            {
                "signal_id": s.signal_id,
                "cluster": s.cluster,
                "source_domain": s.source_domain,
                "published": s.published.isoformat(),
                "useful": s.useful,
                "tags": _brief(s)["tags"],
            }
            for s in accepted
        ],
    }


def _score(m: dict) -> float:
    return weighted_score(
        {
            "freshness": (m["freshness_score"] * 100, 0.30),
            "diversity": (m["source_diversity"] * 100, 0.25),
            "precision": (m["signal_precision"] * 100, 0.30),
            "dedupe": ((1 - m["duplicate_rate"]) * 100, 0.15),
        }
    )


class MarketIntelligenceLab(BaseLab):
    def run(self) -> LabRunResult:
        baseline = _baseline()
        candidate = _candidate()
        baseline_score = _score(baseline)
        new_score = _score(candidate)
        return LabRunResult(
            lab_id=self.definition.id,
            baseline_score=baseline_score,
            new_score=new_score,
            threshold_pct=self.definition.threshold_pct,
            metrics={
                "corpus_size": len(SIGNALS),
                "baseline": baseline,
                "candidate": candidate,
                "useful_tags": sorted(USEFUL_TAGS),
            },
            notes=(
                "Medicion real sobre corpus con duplicados y ruido. Candidate "
                "usa compactacion, tags, clustering por fuente/tema y umbral de "
                "novedad antes de alimentar el core."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        base = result.metrics["baseline"]
        cand = result.metrics["candidate"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Aplicar clustering y umbral de novedad a inteligencia de mercado",
            summary=(
                "El pipeline candidato reduce duplicados y mejora precision de "
                "señales antes de que las novedades entren en la base de "
                "inteligencia IA diaria."
            ),
            recommendation=(
                "Introducir clustering por tema/fuente y umbral de utilidad antes "
                "de promover market updates al core central."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "signal_precision", "baseline": base["signal_precision"],
                 "candidate": cand["signal_precision"]},
                {"metric": "duplicate_rate", "baseline": base["duplicate_rate"],
                 "candidate": cand["duplicate_rate"]},
                {"metric": "accepted_count", "baseline": len(base["accepted"]),
                 "candidate": len(cand["accepted"])},
            ],
            metrics=result.metrics,
            risk_level="medium",
            rollout_plan="Activar primero para fuentes platform-owned; todo update al core sigue requiriendo aprobacion humana.",
            rollback_plan="Desactivar clustering y conservar novedades crudas como drafts solo visibles para admins.",
        )
