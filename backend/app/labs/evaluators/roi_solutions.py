"""ROI & Solutions Lab — eval real del motor de soluciones.

Ejecuta preguntas de golden set contra:
  - baseline: ranking simplista por primera opcion/impacto, sin ajuste real de
    presupuesto.
  - candidate: `solutions_engine.propose`, el motor actual con deteccion de
    presupuesto, catalogo, scoring determinista y ROI.

El lab mide cobertura de catalogo, fit presupuestario, acierto de recomendacion
y calibracion de payback contra bandas esperadas para pymes españolas.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.solutions import catalog
from app.core.solutions.engine import propose
from app.core.solutions.schema import BudgetTier, SolutionOption, budget_rank
from app.labs.base import BaseLab, run_coro, weighted_score
from app.labs.schemas import CoreReportDraft, LabRunResult

TENANT = "__lab_roi_solutions__"


@dataclass(frozen=True)
class SolutionCase:
    query: str
    expected_use_case: str
    budget: BudgetTier
    preferred_option_ids: set[str]
    max_payback_months: float
    min_confidence: int


GOLDEN = [
    SolutionCase(
        "recomiendame un chatbot barato para soporte en una pyme española",
        "chatbot_soporte",
        BudgetTier.BAJO,
        {"chatbot_oss_selfhost"},
        1.5,
        55,
    ),
    SolutionCase(
        "quiero el mejor chatbot aunque sea mas caro para alto volumen",
        "chatbot_soporte",
        BudgetTier.ALTO,
        {"chatbot_enterprise_ccai", "chatbot_saas_gestionado"},
        4.5,
        50,
    ),
    SolutionCase(
        "como priorizo leads comerciales con poco presupuesto y CRM historico",
        "lead_scoring",
        BudgetTier.BAJO,
        {"lead_oss_ml"},
        1.5,
        45,
    ),
    SolutionCase(
        "buscador RAG barato para manuales y procedimientos internos",
        "busqueda_documental",
        BudgetTier.BAJO,
        {"rag_oss"},
        1.6,
        50,
    ),
    SolutionCase(
        "scoring predictivo gestionado para ventas si tenemos presupuesto medio",
        "lead_scoring",
        BudgetTier.MEDIO,
        {"lead_saas_predictivo", "lead_oss_ml"},
        1.2,
        50,
    ),
]


def _baseline_option(case: SolutionCase) -> tuple[str, str, SolutionOption | None]:
    use_case_id, _ = catalog.match_use_case(case.query)
    options = catalog.get_options(use_case_id, TENANT)
    if not options:
        return use_case_id, "generico", None
    # Politica baseline: ignora presupuesto real y elige la opcion con mayor
    # impacto del catalogo; a empate, la primera.
    options.sort(key=lambda o: o.scorecard.get("impacto", 3), reverse=True)
    return use_case_id, options[0].id, options[0]


def _fit(option: SolutionOption | None, budget: BudgetTier) -> float:
    if not option:
        return 0.0
    delta = budget_rank(option.budget_tier) - budget_rank(budget)
    if delta <= 0:
        return 1.0
    if delta == 1:
        return 0.45
    return 0.15


def _payback_ok(option: SolutionOption | None, case: SolutionCase) -> float:
    if not option:
        return 0.0
    confidence_ok = 1.0 if option.roi.confidence >= case.min_confidence else 0.5
    payback_ok = 1.0 if option.roi.payback_months <= case.max_payback_months else 0.0
    return round((confidence_ok + payback_ok) / 2, 4)


def _recommendation_ok(option_id: str | None, case: SolutionCase) -> float:
    return 1.0 if option_id in case.preferred_option_ids else 0.0


async def _candidate_option(case: SolutionCase) -> tuple[str, str | None, SolutionOption | None]:
    proposal = await propose(
        case.query,
        TENANT,
        [],
        client_name="Lab SME",
        data_region="eu",
        budget=case.budget,
    )
    option = next((o for o in proposal.options if o.id == proposal.recommended_id), None)
    return proposal.use_case, proposal.recommended_id, option


def _evaluate_baseline() -> dict:
    rows = []
    for case in GOLDEN:
        use_case_id, option_id, option = _baseline_option(case)
        rows.append(_case_row(case, use_case_id, option_id, option))
    return _aggregate("impact_first_no_budget_fit", rows)


def _evaluate_candidate() -> dict:
    rows = []
    for case in GOLDEN:
        use_case_id, option_id, option = run_coro(_candidate_option(case))
        rows.append(_case_row(case, use_case_id, option_id, option))
    return _aggregate("current_solutions_engine", rows)


def _case_row(
    case: SolutionCase,
    use_case_id: str,
    option_id: str | None,
    option: SolutionOption | None,
) -> dict:
    return {
        "query": case.query,
        "expected_use_case": case.expected_use_case,
        "actual_use_case": use_case_id,
        "recommended_id": option_id,
        "catalog_hit": use_case_id == case.expected_use_case,
        "recommendation_ok": _recommendation_ok(option_id, case),
        "budget_fit": _fit(option, case.budget),
        "payback_ok": _payback_ok(option, case),
        "payback_months": option.roi.payback_months if option else None,
        "confidence": option.roi.confidence if option else None,
    }


def _aggregate(policy: str, rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "policy": policy,
        "catalog_coverage": round(sum(r["catalog_hit"] for r in rows) / n, 4),
        "roi_calibration": round(sum(r["recommendation_ok"] for r in rows) / n, 4),
        "budget_fit": round(sum(r["budget_fit"] for r in rows) / n, 4),
        "payback_accuracy": round(sum(r["payback_ok"] for r in rows) / n, 4),
        "cases": rows,
    }


def _score(m: dict) -> float:
    return weighted_score(
        {
            "roi": (m["roi_calibration"] * 100, 0.30),
            "budget": (m["budget_fit"] * 100, 0.25),
            "coverage": (m["catalog_coverage"] * 100, 0.25),
            "payback": (m["payback_accuracy"] * 100, 0.20),
        }
    )


class RoiSolutionsLab(BaseLab):
    def run(self) -> LabRunResult:
        baseline = _evaluate_baseline()
        candidate = _evaluate_candidate()
        baseline_score = _score(baseline)
        new_score = _score(candidate)
        return LabRunResult(
            lab_id=self.definition.id,
            baseline_score=baseline_score,
            new_score=new_score,
            threshold_pct=self.definition.threshold_pct,
            metrics={
                "golden_set_size": len(GOLDEN),
                "baseline": baseline,
                "candidate": candidate,
            },
            notes=(
                "Medicion real contra el motor de soluciones actual. Compara "
                "ranking simplista sin presupuesto con propose()+scoring "
                "determinista, midiendo fit presupuestario, cobertura y payback."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        base = result.metrics["baseline"]
        cand = result.metrics["candidate"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Mejorar ranking de soluciones para pymes españolas",
            summary=(
                "El motor actual con scoring por presupuesto y ROI supera al "
                "ranking simplista del catalogo en fit presupuestario y acierto "
                "de recomendacion sobre el golden set."
            ),
            recommendation=(
                "Mantener y versionar perfiles de presupuesto para pymes españolas; "
                "ampliar el golden set por vertical antes de añadir mas vendors."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "budget_fit", "baseline": base["budget_fit"],
                 "candidate": cand["budget_fit"]},
                {"metric": "roi_calibration", "baseline": base["roi_calibration"],
                 "candidate": cand["roi_calibration"]},
                {"metric": "payback_accuracy", "baseline": base["payback_accuracy"],
                 "candidate": cand["payback_accuracy"]},
            ],
            metrics=result.metrics,
            risk_level="low",
            rollout_plan="Aplicar a chatbot, lead scoring y busqueda documental; revisar aceptacion de recomendaciones por humanos.",
            rollback_plan="Volver a pesos de scoring anteriores y congelar contribuciones nuevas del catalogo.",
        )
