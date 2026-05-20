"""Model Routing & Cost Lab — cálculo REAL (no números mágicos).

Calcula coste, calidad (modelada), latencia y precisión de escalado a premium a
partir de supuestos EXPLÍCITOS y editables:
  - una tabla de precios por tier (€/1M tokens),
  - una mezcla de carga mensual (tareas, volumen, tokens, tier mínimo necesario),
  - la política de enrutamiento baseline vs. candidate.

Compara la política actual (baseline) con una candidata que (a) baja tareas
rutinarias de medium→cheap cuando el tier mínimo lo permite y (b) corrige una
sobre-escalada a premium. Todo el resultado se deriva de las tablas: si cambias
precios o mezcla, el resultado cambia. La calidad es un PROXY modelado (por tier
mínimo) hasta tener evals reales; se indica así en las notas.
"""
from __future__ import annotations

from app.labs.base import BaseLab, weighted_score
from app.labs.schemas import CoreReportDraft, LabRunResult

# € por 1M tokens (blended in+out). Ajustar a precios reales del proveedor.
PRICE_EUR_PER_1M = {"cheap": 0.30, "medium": 1.20, "premium": 12.00}
# Calidad base por tier si CUMPLE el tier mínimo necesario (proxy 0-1).
TIER_QUALITY = {"cheap": 0.86, "medium": 0.95, "premium": 1.0}
# Latencia p95 modelada por tier (ms).
TIER_LATENCY_MS = {"cheap": 1800, "medium": 4200, "premium": 9000}
TIER_RANK = {"cheap": 0, "medium": 1, "premium": 2}
COST_NORM = 10.0          # €/1k tareas que mapea a cost_score = 0
UNDERSERVE_PENALTY = 0.75  # factor si el tier asignado < tier mínimo necesario

# Mezcla de carga mensual. min_tier = tier mínimo que da calidad aceptable.
WORKLOAD = [
    # task, volumen/mes, tokens medios, min_tier, baseline_tier, candidate_tier
    ("intent_routing",      60000,  400, "cheap",   "cheap",   "cheap"),
    ("verify",              40000, 1200, "cheap",   "cheap",   "cheap"),
    ("summarize_extract",   30000, 2500, "cheap",   "medium",  "cheap"),
    ("rag_answer",          25000, 3500, "medium",  "medium",  "medium"),
    ("solution_synthesis",   8000, 4000, "medium",  "premium", "medium"),
    ("strategy_synthesis",   3000, 6000, "premium", "premium", "premium"),
    ("grc_synthesis",        2500, 6000, "premium", "premium", "premium"),
    ("doc_triage",          20000, 1500, "cheap",   "medium",  "cheap"),
]


def _task_quality(min_tier: str, assigned: str) -> float:
    q = TIER_QUALITY[assigned]
    if TIER_RANK[assigned] < TIER_RANK[min_tier]:
        q *= UNDERSERVE_PENALTY
    return q


def _evaluate_policy(policy_index: int) -> dict:
    """policy_index: 4 = baseline_tier, 5 = candidate_tier (posición en la tupla)."""
    total_tasks = sum(row[1] for row in WORKLOAD)
    total_cost = 0.0
    q_weighted = 0.0
    lat_weighted = 0.0
    premium_assigned = 0
    premium_needed_and_assigned = 0
    for task, volume, tokens, min_tier, base_tier, cand_tier in WORKLOAD:
        assigned = base_tier if policy_index == 4 else cand_tier
        tokens_m = volume * tokens / 1_000_000
        total_cost += tokens_m * PRICE_EUR_PER_1M[assigned]
        q_weighted += volume * _task_quality(min_tier, assigned)
        lat_weighted += volume * TIER_LATENCY_MS[assigned]
        if assigned == "premium":
            premium_assigned += 1
            if min_tier == "premium":
                premium_needed_and_assigned += 1
    cost_per_1k = total_cost / (total_tasks / 1000)
    precision = (premium_needed_and_assigned / premium_assigned) if premium_assigned else 1.0
    return {
        "monthly_cost_eur": round(total_cost, 2),
        "cost_per_1k_tasks": round(cost_per_1k, 3),
        "quality_score": round(q_weighted / total_tasks * 100, 2),
        "latency_p95_ms": round(lat_weighted / total_tasks),
        "premium_escalation_precision": round(precision, 3),
    }


def _score(m: dict) -> float:
    cost_score = max(0.0, 100 * (1 - m["cost_per_1k_tasks"] / COST_NORM))
    latency_score = max(0.0, 100 - m["latency_p95_ms"] / 120)
    return weighted_score(
        {
            "quality": (m["quality_score"], 0.45),
            "cost": (cost_score, 0.25),
            "latency": (latency_score, 0.10),
            "routing": (m["premium_escalation_precision"] * 100, 0.20),
        }
    )


class ModelRoutingCostLab(BaseLab):
    def run(self) -> LabRunResult:
        baseline = _evaluate_policy(4)
        candidate = _evaluate_policy(5)
        baseline_score = _score(baseline)
        new_score = _score(candidate)
        cost_reduction_pct = round(
            (baseline["monthly_cost_eur"] - candidate["monthly_cost_eur"])
            / baseline["monthly_cost_eur"] * 100,
            2,
        ) if baseline["monthly_cost_eur"] else 0.0

        return LabRunResult(
            lab_id=self.definition.id,
            baseline_score=baseline_score,
            new_score=new_score,
            threshold_pct=self.definition.threshold_pct,
            metrics={
                "baseline": {**baseline, "policy": "actual"},
                "candidate": {
                    **candidate,
                    "policy": "cheap-first en tareas de tier mínimo bajo + "
                              "corrección de sobre-escalada a premium",
                },
                "cost_reduction_pct": cost_reduction_pct,
                "assumptions": {
                    "price_eur_per_1m": PRICE_EUR_PER_1M,
                    "cost_norm_eur_per_1k_tasks": COST_NORM,
                    "tier_quality_proxy": TIER_QUALITY,
                    "workload_total_tasks": sum(r[1] for r in WORKLOAD),
                },
            },
            notes=(
                "Cálculo real desde tabla de precios y mezcla de carga editables. "
                "quality_score es un PROXY modelado por tier mínimo; reemplazar por "
                "evals reales (LLM-judge/Ragas) cuando estén disponibles. La "
                "candidata reduce coste y mejora la precisión de escalado a "
                "premium, con una caída de calidad marginal y controlada."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        base = result.metrics["baseline"]
        cand = result.metrics["candidate"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Optimizar el enrutamiento híbrido para reducir el TCO",
            summary=(
                "Una política cheap-first para tareas rutinarias y la corrección "
                "de la sobre-escalada a premium reducen el coste manteniendo la "
                "calidad dentro de un margen aceptable."
            ),
            recommendation=(
                "Escalonar la nueva política de routing en flujos no-GRC primero "
                "(síntesis de soluciones, resúmenes, triaje documental), comparar "
                "contra muestras valoradas por humanos y luego incluir GRC con "
                "umbrales más estrictos."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "cost_reduction_pct", "value": result.metrics["cost_reduction_pct"]},
                {"metric": "monthly_cost_eur", "baseline": base["monthly_cost_eur"],
                 "candidate": cand["monthly_cost_eur"]},
                {"metric": "premium_escalation_precision",
                 "baseline": base["premium_escalation_precision"],
                 "candidate": cand["premium_escalation_precision"]},
                {"metric": "quality_score", "baseline": base["quality_score"],
                 "candidate": cand["quality_score"]},
            ],
            metrics=result.metrics,
            risk_level="medium",
            rollout_plan=(
                "Desplegar en flujos no-GRC primero, comparar contra muestras "
                "valoradas por humanos, después incluir GRC con umbrales estrictos."
            ),
            rollback_plan="Restaurar la tabla de routing y los umbrales de escalado anteriores.",
        )
