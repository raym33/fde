from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.core.schemas import RetrievedChunk
from app.security import pii


SensitivityLevel = str


_REGULATED_TERMS = {
    "patient": "health data",
    "paciente": "health data",
    "historia clínica": "health data",
    "historia clinica": "health data",
    "medical record": "health data",
    "expediente": "legal case file",
    "diagnóstico": "health data",
    "diagnostico": "health data",
    "salary": "employment data",
    "salario": "employment data",
    "nomina": "payroll data",
    "nómina": "payroll data",
}

_CONFIDENTIAL_TERMS = {
    "contrato": "contract content",
    "contract": "contract content",
    "invoice": "invoice data",
    "factura": "invoice data",
    "supplier": "supplier data",
    "proveedor": "supplier data",
    "pricing": "pricing data",
    "precio": "pricing data",
    "erp": "internal system context",
    "crm": "internal customer context",
}

_INTERNAL_TERMS = {
    "policy": "internal policy",
    "política": "internal policy",
    "politica": "internal policy",
    "procedure": "internal procedure",
    "procedimiento": "internal procedure",
    "manual": "internal manual",
    "roadmap": "internal planning",
    "playbook": "internal playbook",
}


@dataclass(frozen=True)
class SensitivityAssessment:
    level: SensitivityLevel
    labels: list[str]
    reasons: list[str]
    pii_placeholders: list[str]


def classify_sensitivity(message: str, chunks: Iterable[RetrievedChunk]) -> SensitivityAssessment:
    haystacks = [message]
    haystacks.extend(chunk.text[:1000] for chunk in chunks)
    lowered = "\n".join(haystacks).lower()
    _, pii_map = pii.redact("\n".join(haystacks))

    labels: list[str] = []
    reasons: list[str] = []

    if pii_map:
        labels.append("pii")
        reasons.append(f"Detected PII placeholders: {', '.join(sorted(pii_map.keys()))}")

    for term, label in _REGULATED_TERMS.items():
        if term in lowered:
            labels.append("regulated")
            reasons.append(f"Detected regulated content marker: {label}")

    for term, label in _CONFIDENTIAL_TERMS.items():
        if term in lowered:
            labels.append("confidential")
            reasons.append(f"Detected confidential content marker: {label}")

    for term, label in _INTERNAL_TERMS.items():
        if term in lowered:
            labels.append("internal")
            reasons.append(f"Detected internal content marker: {label}")

    if "pii" in labels or "regulated" in labels:
        level = "regulated"
    elif "confidential" in labels:
        level = "confidential"
    elif "internal" in labels or haystacks:
        level = "internal"
    else:
        level = "public"

    deduped_reasons = list(dict.fromkeys(reasons))
    deduped_labels = list(dict.fromkeys(labels))
    return SensitivityAssessment(
        level=level,
        labels=deduped_labels,
        reasons=deduped_reasons,
        pii_placeholders=sorted(pii_map.keys()),
    )


def can_escalate_to_external(level: SensitivityLevel, allow_sensitive: bool) -> bool:
    if allow_sensitive:
        return True
    return level in {"public", "internal"}
