"""Motor de soluciones: reúne candidatos, los puntúa y recomienda la mejor.

Flujo:
  1. Detecta el presupuesto del cliente y el caso de uso de la pregunta.
  2. Reúne candidatos: catálogo curado + contribuciones humanas (+ web/LLM para
     casos no catalogados).
  3. Enriquece con opciones de mercado al día vía búsqueda web (si disponible).
  4. PUNTÚA Y RANKEA EN CÓDIGO (scoring.py) — determinista y auditable.
  5. Recomienda la mejor y deja una narrativa ejecutiva (LLM) alrededor.

`render_markdown` produce la propuesta lista para mostrar (tabla comparativa +
detalle de la recomendada). Los números nunca los inventa el LLM.
"""
from __future__ import annotations

from app.core.schemas import Citation, RetrievedChunk
from app.core.solutions import catalog
from app.core.solutions.schema import (
    BudgetTier,
    Phase,
    ROIEstimate,
    SolutionOption,
    SolutionProposal,
)
from app.core.solutions.scoring import rank_options
from app.tools import web_search

_BUDGET_BAJO = ["bajo presupuesto", "presupuesto bajo", "presupuesto ajustado",
                "barat", "económic", "economic", "low cost", "low-cost",
                "poco presupuesto", "sin apenas", "pyme pequeña", "gratis",
                "coste mínimo", "coste minimo", "asequible", "ajustad"]
_BUDGET_ALTO = ["sin límite de presupuesto", "sin limite de presupuesto",
                "presupuesto alto", "gran presupuesto", "enterprise",
                "lo mejor sin importar el coste"]


def detect_budget(query: str, default: BudgetTier = BudgetTier.MEDIO) -> BudgetTier:
    q = query.lower()
    if any(k in q for k in _BUDGET_BAJO):
        return BudgetTier.BAJO
    if any(k in q for k in _BUDGET_ALTO):
        return BudgetTier.ALTO
    return default


def _generic_option() -> SolutionOption:
    """Fallback para casos de uso no catalogados (marcado como preliminar)."""
    return SolutionOption(
        id="generico_oss",
        title="Enfoque open source auto-gestionado (preliminar)",
        summary=(
            "Caso de uso no catalogado todavía: propuesta preliminar basada en "
            "componentes open source en la UE. Requiere refinamiento con un "
            "experto y, si procede, una contribución al catálogo."
        ),
        approach="hybrid",
        budget_tier=BudgetTier.BAJO,
        tools=[],
        scorecard={"impacto": 3, "coste": 2, "esfuerzo": 3, "riesgo": 3,
                   "tiempo_a_valor": 3, "cumplimiento": 4},
        roi=ROIEstimate(
            setup_cost_eur=5000, monthly_cost_eur=300, annual_benefit_eur=30000,
            payback_months=2.0, confidence=35,
            assumptions=["Estimación preliminar; validar con el cliente"],
        ),
        implementation=[
            Phase(name="Descubrimiento y definición", weeks=2,
                  owner="humano+IA", deliverable="Caso de uso acotado"),
            Phase(name="Prototipo", weeks=3, owner="humano+IA",
                  deliverable="PoC evaluable"),
        ],
        risks=["Caso no catalogado: confianza baja hasta validación"],
    )


async def propose(
    question: str,
    tenant_id: str,
    chunks: list[RetrievedChunk],
    *,
    client_name: str,
    data_region: str,
    budget: BudgetTier | None = None,
) -> SolutionProposal:
    client_budget = budget or detect_budget(question)
    use_case_id, use_case_label = catalog.match_use_case(question)

    options = catalog.get_options(use_case_id, tenant_id)
    if not options:
        options = [_generic_option()]

    # Enriquecimiento de mercado al día (si hay proveedor de búsqueda).
    web_sources: list[Citation] = []
    if web_search.is_available():
        for r in await web_search.search(f"{use_case_label} solución IA pyme", 5):
            web_sources.append(
                Citation(source_id=r.url, source_type="web",
                         snippet=r.snippet, date=r.published)
            )

    # Citas de catálogo en cada opción.
    for opt in options:
        opt.sources.append(
            Citation(source_id=f"catalog:{use_case_id}/{opt.id}",
                     source_type="knowledge_base",
                     snippet="Opción del catálogo curado de VirtuDirector IA")
        )

    ranked = rank_options(options, client_budget)
    recommended = ranked[0] if ranked else None
    if recommended and web_sources:
        recommended.sources.extend(web_sources)

    proposal = SolutionProposal(
        question=question,
        use_case=use_case_id,
        client_budget=client_budget,
        recommended_id=recommended.id if recommended else None,
        options=ranked,
    )
    proposal.rationale = _deterministic_rationale(proposal, use_case_label)
    return proposal


def _deterministic_rationale(p: SolutionProposal, label: str) -> str:
    if not p.options:
        return "No se encontraron opciones para esta pregunta."
    rec = p.options[0]
    return (
        f"Para «{label}» con presupuesto {p.client_budget.value}, la opción "
        f"recomendada es **{rec.title}** (score {rec.total_score}/100): mejor "
        f"equilibrio entre impacto, coste y ajuste a presupuesto. Payback "
        f"estimado de {rec.roi.payback_months:.1f} meses "
        f"(confianza {rec.roi.confidence}%)."
    )


# ── Render determinista a Markdown ─────────────────────────────────
def render_markdown(p: SolutionProposal) -> str:
    if not p.options:
        return "No se encontraron soluciones candidatas para esta pregunta."

    rec = p.options[0]
    lines: list[str] = []
    lines.append(f"## Mejor solución recomendada: {rec.title}")
    lines.append("")
    lines.append(p.rationale)
    lines.append("")

    # Tabla comparativa
    lines.append("### Comparativa de opciones")
    lines.append("")
    lines.append(
        "| Solución | Presupuesto | Score | Coste inicial | Coste/mes | "
        "Payback | Confianza |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for o in p.options:
        star = " ⭐" if o.id == p.recommended_id else ""
        lines.append(
            f"| {o.title}{star} | {o.budget_tier.value} | {o.total_score} | "
            f"{o.roi.setup_cost_eur:,}€ | {o.roi.monthly_cost_eur:,}€ | "
            f"{o.roi.payback_months:.1f} m | {o.roi.confidence}% |"
        )
    lines.append("")

    # Detalle de la recomendada
    lines.append(f"### Detalle de la recomendada: {rec.title}")
    lines.append("")
    if rec.tools:
        lines.append("**Herramientas / proveedores:**")
        lines.append("")
        for t in rec.tools:
            cost = (
                "gratis/variable"
                if not t.monthly_cost_eur
                else f"{t.monthly_cost_eur[0]:,}–{t.monthly_cost_eur[1]:,}€/mes"
            )
            flags = []
            if t.eu_hosting:
                flags.append("datos UE")
            if t.spanish_support:
                flags.append("ES")
            flag = f" ({', '.join(flags)})" if flags else ""
            vendor = f" — {t.vendor}" if t.vendor else ""
            lines.append(f"- **{t.name}**{vendor} · {t.kind} · {cost}{flag}. {t.notes}")
        lines.append("")

    lines.append("**ROI estimado:**")
    lines.append("")
    lines.append(
        f"- Inversión inicial: {rec.roi.setup_cost_eur:,}€ · "
        f"Recurrente: {rec.roi.monthly_cost_eur:,}€/mes · "
        f"Beneficio anual estimado: {rec.roi.annual_benefit_eur:,}€ · "
        f"Payback: {rec.roi.payback_months:.1f} meses · "
        f"Confianza: {rec.roi.confidence}%"
    )
    if rec.roi.assumptions:
        lines.append(f"- Supuestos: {'; '.join(rec.roi.assumptions)}")
    lines.append("")

    if rec.implementation:
        lines.append("**Plan de implementación:**")
        lines.append("")
        for i, ph in enumerate(rec.implementation, 1):
            lines.append(
                f"{i}. {ph.name} — {ph.weeks} sem · owner: {ph.owner} · "
                f"entregable: {ph.deliverable}"
            )
        lines.append("")

    if rec.risks:
        lines.append("**Riesgos principales:** " + "; ".join(rec.risks))
        lines.append("")

    lines.append(f"_{p.disclaimer}_")
    return "\n".join(lines)
