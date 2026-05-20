"""Modelos del motor de soluciones.

Una "propuesta" contiene varias soluciones candidatas, cada una con sus
herramientas/proveedores concretos, una estimación de ROI, un plan de
implementación por fases y un *scorecard*. El scoring y el ranking se calculan
en código (ver `scoring.py`), no los genera el LLM.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.core.schemas import Citation


class BudgetTier(str, Enum):
    BAJO = "bajo"      # pyme con presupuesto ajustado
    MEDIO = "medio"
    ALTO = "alto"


_BUDGET_ORDER = {BudgetTier.BAJO: 0, BudgetTier.MEDIO: 1, BudgetTier.ALTO: 2}


def budget_rank(t: BudgetTier) -> int:
    return _BUDGET_ORDER[t]


class Tool(BaseModel):
    name: str
    vendor: str | None = None
    kind: str                       # "open_source" | "saas" | "servicio"
    monthly_cost_eur: tuple[int, int] | None = None  # (min, max); None = gratis/variable
    eu_hosting: bool = False        # datos en UE (RGPD-friendly)
    spanish_support: bool = False   # soporte/UX en español
    notes: str = ""


class ROIEstimate(BaseModel):
    setup_cost_eur: int             # coste de puesta en marcha
    monthly_cost_eur: int           # coste recurrente
    annual_benefit_eur: int         # beneficio anual estimado (ahorro/ingreso)
    payback_months: float           # meses hasta recuperar la inversión
    confidence: int                 # 0-100
    assumptions: list[str] = Field(default_factory=list)


class Phase(BaseModel):
    name: str
    weeks: int
    owner: str                      # "humano" | "IA" | "humano+IA"
    deliverable: str


# Dimensiones del scorecard (cada una 1-5). coste/esfuerzo/riesgo/tiempo son
# "inversas": menos es mejor, y el scoring las invierte.
SCORE_DIMENSIONS = [
    "impacto",
    "coste",
    "esfuerzo",
    "riesgo",
    "tiempo_a_valor",
    "cumplimiento",
    "ajuste_presupuesto",
]


class SolutionOption(BaseModel):
    id: str
    title: str
    summary: str
    approach: str                   # "build" | "buy" | "hybrid"
    budget_tier: BudgetTier
    tools: list[Tool] = Field(default_factory=list)
    scorecard: dict[str, int] = Field(default_factory=dict)  # dimensión -> 1..5
    roi: ROIEstimate
    implementation: list[Phase] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)

    # Rellenado por el scorer:
    total_score: float = 0.0


class SolutionProposal(BaseModel):
    question: str
    use_case: str                   # categoría detectada (p. ej. "chatbot_soporte")
    client_budget: BudgetTier
    recommended_id: str | None = None
    options: list[SolutionOption] = Field(default_factory=list)
    rationale: str = ""             # por qué la recomendada gana (narrativa)
    disclaimer: str = (
        "Esto no es asesoramiento legal ni financiero — las cifras son "
        "estimaciones que deben validarse con datos reales del cliente."
    )
