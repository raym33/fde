"""Scoring determinista de soluciones.

Principio clave: el ranking lo calcula este código, NO el LLM. Cada solución se
puntua 0-100 como suma ponderada de sus dimensiones. El perfil de pesos depende
del presupuesto del cliente (una pyme con presupuesto bajo penaliza más el coste
y prima el ajuste a presupuesto). El "ajuste_presupuesto" se calcula en función
del tier de la solución frente al del cliente, para que la sensibilidad al
presupuesto sea real y no un número escrito a mano.
"""
from __future__ import annotations

from app.core.solutions.schema import (
    BudgetTier,
    SolutionOption,
    budget_rank,
)

# Dimensiones "inversas": un valor alto (1-5) significa MÁS coste/esfuerzo/etc.,
# y por tanto PEOR. Se invierten al puntuar.
_INVERSE = {"coste", "esfuerzo", "riesgo", "tiempo_a_valor"}

# Perfiles de peso por presupuesto del cliente (suman 1.0).
_WEIGHTS: dict[BudgetTier, dict[str, float]] = {
    BudgetTier.BAJO: {
        "impacto": 0.20,
        "coste": 0.22,
        "esfuerzo": 0.12,
        "riesgo": 0.10,
        "tiempo_a_valor": 0.10,
        "cumplimiento": 0.10,
        "ajuste_presupuesto": 0.16,
    },
    BudgetTier.MEDIO: {
        "impacto": 0.26,
        "coste": 0.16,
        "esfuerzo": 0.12,
        "riesgo": 0.12,
        "tiempo_a_valor": 0.12,
        "cumplimiento": 0.12,
        "ajuste_presupuesto": 0.10,
    },
    BudgetTier.ALTO: {
        "impacto": 0.34,
        "coste": 0.08,
        "esfuerzo": 0.10,
        "riesgo": 0.14,
        "tiempo_a_valor": 0.12,
        "cumplimiento": 0.14,
        "ajuste_presupuesto": 0.08,
    },
}


def budget_fit_value(option_tier: BudgetTier, client_tier: BudgetTier) -> int:
    """1-5: cuánto encaja el coste de la solución en el presupuesto del cliente."""
    delta = budget_rank(option_tier) - budget_rank(client_tier)
    if delta <= 0:
        return 5          # cabe en el presupuesto (o sobra)
    if delta == 1:
        return 2          # un escalón por encima
    return 1              # claramente fuera de presupuesto


def score_option(option: SolutionOption, client_budget: BudgetTier) -> float:
    weights = _WEIGHTS[client_budget]
    sc = dict(option.scorecard)
    # ajuste_presupuesto se calcula, no se confía al catálogo/LLM.
    sc["ajuste_presupuesto"] = budget_fit_value(option.budget_tier, client_budget)

    total = 0.0
    for dim, w in weights.items():
        raw = sc.get(dim, 3)            # 3 = neutro si falta
        raw = max(1, min(5, int(raw)))
        norm = (6 - raw) if dim in _INVERSE else raw   # invertir las inversas
        total += w * (norm / 5.0)       # normaliza a 0..1
    option.total_score = round(total * 100, 1)
    option.scorecard = sc
    return option.total_score


def rank_options(
    options: list[SolutionOption], client_budget: BudgetTier
) -> list[SolutionOption]:
    for opt in options:
        score_option(opt, client_budget)
    # Orden: score desc; a igualdad, menor payback y menor coste mensual.
    return sorted(
        options,
        key=lambda o: (-o.total_score, o.roi.payback_months, o.roi.monthly_cost_eur),
    )
