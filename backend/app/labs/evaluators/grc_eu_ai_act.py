"""GRC & EU AI Act Lab — medicion real de reglas de readiness.

Evalua dos politicas de control contra escenarios esperados:
  - baseline: checklist generico centrado en deployer.
  - candidate: controles especificos por rol (provider/deployer/importer/
    distributor) + fuentes obligatorias + disclaimer.

No es asesoramiento legal; es una evaluacion automatizada de cobertura interna.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.labs.base import BaseLab, weighted_score
from app.labs.registry import register_lab
from app.labs.schemas import CoreReportDraft, LabRunResult


@dataclass(frozen=True)
class GrcCase:
    case_id: str
    description: str
    role: str
    expected_risk: str
    expected_obligations: set[str]
    expected_policies: set[str]


GOLDEN = [
    GrcCase(
        "support_chatbot",
        "Pyme despliega chatbot de soporte con avisos al usuario y escalado humano.",
        "deployer",
        "limited",
        {"transparency_notice", "human_oversight", "logging", "data_governance"},
        {"ai_use_policy", "incident_response"},
    ),
    GrcCase(
        "recruiting_cv_ranker",
        "Sistema de ranking de CV para seleccion de personal.",
        "deployer",
        "high",
        {"risk_management", "data_governance", "human_oversight", "logging", "fundamental_rights_assessment"},
        {"ai_use_policy", "high_risk_register", "human_oversight_policy"},
    ),
    GrcCase(
        "credit_scoring",
        "Scoring de solvencia para conceder credito a clientes.",
        "provider",
        "high",
        {"risk_management", "quality_management", "technical_documentation", "conformity_assessment", "post_market_monitoring"},
        {"quality_management_policy", "model_risk_policy", "incident_response"},
    ),
    GrcCase(
        "internal_doc_search",
        "Buscador RAG interno sobre procedimientos sin decision automatizada.",
        "deployer",
        "minimal",
        {"access_control", "data_governance", "logging"},
        {"ai_use_policy", "data_retention_policy"},
    ),
    GrcCase(
        "imported_biometric_tool",
        "Importa una herramienta biometrica de proveedor tercero para acceso a oficinas.",
        "importer",
        "high",
        {"supplier_due_diligence", "conformity_check", "risk_management", "human_oversight"},
        {"vendor_ai_due_diligence", "high_risk_register", "incident_response"},
    ),
]

SOURCE_REQUIREMENTS = {
    "eu_ai_act_timeline",
    "gdpr_basis",
    "nist_ai_rmf",
    "iso_42001",
}


def _baseline(case: GrcCase) -> dict:
    obligations = {"transparency_notice", "human_oversight", "logging", "data_governance"}
    policies = {"ai_use_policy", "incident_response"}
    sources = {"eu_ai_act_timeline", "gdpr_basis"}
    risk = "high" if any(k in case.description.lower() for k in ["cv", "credito", "biometric"]) else "limited"
    return _row(case, risk, obligations, policies, sources, "generic_deployer_checklist")


def _candidate(case: GrcCase) -> dict:
    common = {"data_governance", "logging"}
    by_role = {
        "deployer": {"human_oversight", "transparency_notice", "access_control"},
        "provider": {"quality_management", "technical_documentation", "conformity_assessment", "post_market_monitoring"},
        "importer": {"supplier_due_diligence", "conformity_check", "human_oversight"},
        "distributor": {"supplier_due_diligence", "conformity_check"},
    }
    risk_controls = {
        "high": {"risk_management", "fundamental_rights_assessment"},
        "limited": {"transparency_notice", "human_oversight"},
        "minimal": {"access_control"},
    }
    policies = {
        "ai_use_policy",
        "incident_response",
        "data_retention_policy",
    }
    if case.expected_risk == "high":
        policies |= {"high_risk_register", "human_oversight_policy", "model_risk_policy"}
    if case.role in {"provider"}:
        policies |= {"quality_management_policy"}
    if case.role in {"importer", "distributor"}:
        policies |= {"vendor_ai_due_diligence"}

    risk = _classify_risk(case)
    obligations = common | by_role.get(case.role, set()) | risk_controls.get(risk, set())
    return _row(case, risk, obligations, policies, SOURCE_REQUIREMENTS, "role_specific_controls")


def _classify_risk(case: GrcCase) -> str:
    text = case.description.lower()
    if any(k in text for k in ["cv", "credito", "biometric", "biometr"]):
        return "high"
    if any(k in text for k in ["chatbot", "usuario", "soporte"]):
        return "limited"
    return "minimal"


def _row(
    case: GrcCase,
    risk: str,
    obligations: set[str],
    policies: set[str],
    sources: set[str],
    policy: str,
) -> dict:
    obligation_hits = len(case.expected_obligations & obligations)
    policy_hits = len(case.expected_policies & policies)
    return {
        "case_id": case.case_id,
        "policy": policy,
        "role": case.role,
        "expected_risk": case.expected_risk,
        "risk": risk,
        "risk_ok": risk == case.expected_risk,
        "obligation_coverage": round(obligation_hits / len(case.expected_obligations), 4),
        "policy_completeness": round(policy_hits / len(case.expected_policies), 4),
        "source_coverage": round(len(SOURCE_REQUIREMENTS & sources) / len(SOURCE_REQUIREMENTS), 4),
        "obligations": sorted(obligations),
        "policies": sorted(policies),
        "sources": sorted(sources),
    }


def _aggregate(policy: str, rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "policy": policy,
        "obligation_coverage": round(sum(r["obligation_coverage"] for r in rows) / n, 4),
        "risk_classification_accuracy": round(sum(r["risk_ok"] for r in rows) / n, 4),
        "policy_completeness": round(sum(r["policy_completeness"] for r in rows) / n, 4),
        "source_coverage": round(sum(r["source_coverage"] for r in rows) / n, 4),
        "cases": rows,
    }


def _score(m: dict) -> float:
    return weighted_score(
        {
            "obligations": (m["obligation_coverage"] * 100, 0.30),
            "risk": (m["risk_classification_accuracy"] * 100, 0.30),
            "policy": (m["policy_completeness"] * 100, 0.25),
            "sources": (m["source_coverage"] * 100, 0.15),
        }
    )


@register_lab("grc_eu_ai_act")
class GrcEuAiActLab(BaseLab):
    def run(self) -> LabRunResult:
        baseline = _aggregate("generic_deployer_checklist", [_baseline(c) for c in GOLDEN])
        candidate = _aggregate("role_specific_controls", [_candidate(c) for c in GOLDEN])
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
                "source_requirements": sorted(SOURCE_REQUIREMENTS),
                "disclaimer": "This is not legal advice — consult qualified counsel.",
            },
            notes=(
                "Medicion real sobre escenarios EU AI Act/RGPD. La candidata "
                "clasifica riesgo y controles por rol, y exige fuentes base."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        base = result.metrics["baseline"]
        cand = result.metrics["candidate"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Fortalecer workflow EU AI Act con controles por rol",
            summary=(
                "Los controles por rol mejoran cobertura de obligaciones, "
                "clasificacion de riesgo, politicas y fuentes frente al checklist "
                "generico centrado en deployer."
            ),
            recommendation=(
                "Actualizar el workflow EU AI Act para preguntar primero si el "
                "cliente actua como provider, deployer, importer o distributor, "
                "y generar controles/politicas por rol."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "obligation_coverage", "baseline": base["obligation_coverage"],
                 "candidate": cand["obligation_coverage"]},
                {"metric": "risk_classification_accuracy", "baseline": base["risk_classification_accuracy"],
                 "candidate": cand["risk_classification_accuracy"]},
                {"metric": "source_coverage", "baseline": base["source_coverage"],
                 "candidate": cand["source_coverage"]},
            ],
            metrics=result.metrics,
            risk_level="high",
            rollout_plan="Versionar el workflow GRC; exigir disclaimer legal, rol del cliente y citas de fuentes en cada salida.",
            rollback_plan="Volver al checklist generico y dejar los controles por rol como borrador interno.",
        )
