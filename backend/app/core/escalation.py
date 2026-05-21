from __future__ import annotations

from typing import Iterable

from app.config import get_settings
from app.core import runtime_policy
from app.core.schemas import Intent, RetrievedChunk, VerifierVerdict


CRITICAL_INTENTS = {
    Intent.GRC.value,
    Intent.STRATEGY.value,
    Intent.DELIVERABLE.value,
}

SENSITIVE_TERMS = {
    "dni",
    "iban",
    "patient",
    "paciente",
    "clinical",
    "clinica",
    "clínica",
    "medical",
    "medica",
    "médica",
    "historia clinica",
    "historia clínica",
    "expediente",
    "contract",
    "contrato",
}


def user_requested_premium(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in {
            "version premium",
            "premium version",
            "use premium",
            "usa premium",
            "frontier model",
            "modelo premium",
        }
    )


def contains_sensitive_content(message: str, chunks: Iterable[RetrievedChunk]) -> bool:
    haystacks = [message.lower()]
    haystacks.extend(chunk.text.lower()[:800] for chunk in chunks)
    return any(term in haystack for haystack in haystacks for term in SENSITIVE_TERMS)


def estimate_context_size(message: str, chunks: Iterable[RetrievedChunk]) -> int:
    return len(message) + sum(len(chunk.text) for chunk in chunks)


def should_escalate(
    *,
    intent: Intent,
    message: str,
    verdict: VerifierVerdict | None,
    chunks: list[RetrievedChunk],
) -> bool:
    settings = get_settings()
    policy = runtime_policy.current_policy()
    if not policy.escalation_enabled:
        return False
    if policy.premium_provider == "lmstudio":
        return False

    intent_name = intent.value.lower()
    allowed_intents = {
        item.strip().lower()
        for item in policy.escalation_allowed_intents.split(",")
        if item.strip()
    }
    if intent_name not in allowed_intents and not user_requested_premium(message):
        return False

    if contains_sensitive_content(message, chunks) and not policy.escalation_allow_sensitive:
        return False

    if user_requested_premium(message):
        return True
    if intent_name in CRITICAL_INTENTS:
        return True
    if estimate_context_size(message, chunks) > settings.local_context_limit:
        return True
    if verdict and not verdict.approved:
        return True
    return False
