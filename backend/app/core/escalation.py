from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.config import get_settings
from app.core import runtime_policy
from app.core.schemas import Intent, RetrievedChunk, VerifierVerdict
from app.security import sensitivity


CRITICAL_INTENTS = {
    Intent.GRC.value,
    Intent.STRATEGY.value,
    Intent.DELIVERABLE.value,
}

@dataclass(frozen=True)
class EscalationDecision:
    escalate: bool
    provider: str
    sensitivity_level: str
    sensitivity_labels: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    blocked_reason: str | None = None


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

def estimate_context_size(message: str, chunks: Iterable[RetrievedChunk]) -> int:
    return len(message) + sum(len(chunk.text) for chunk in chunks)


def escalation_decision(
    *,
    intent: Intent,
    message: str,
    verdict: VerifierVerdict | None,
    chunks: list[RetrievedChunk],
) -> EscalationDecision:
    settings = get_settings()
    policy = runtime_policy.current_policy()
    assessment = sensitivity.classify_sensitivity(message, chunks)
    reasons: list[str] = []

    if not policy.escalation_enabled:
        return EscalationDecision(
            escalate=False,
            provider=policy.premium_provider,
            sensitivity_level=assessment.level,
            sensitivity_labels=assessment.labels,
            reasons=assessment.reasons,
            blocked_reason="Escalation disabled by policy.",
        )
    if policy.premium_provider == "lmstudio":
        return EscalationDecision(
            escalate=False,
            provider=policy.premium_provider,
            sensitivity_level=assessment.level,
            sensitivity_labels=assessment.labels,
            reasons=assessment.reasons,
            blocked_reason="Premium provider is configured as LM Studio.",
        )

    intent_name = intent.value.lower()
    allowed_intents = {
        item.strip().lower()
        for item in policy.escalation_allowed_intents.split(",")
        if item.strip()
    }
    if intent_name not in allowed_intents and not user_requested_premium(message):
        return EscalationDecision(
            escalate=False,
            provider=policy.premium_provider,
            sensitivity_level=assessment.level,
            sensitivity_labels=assessment.labels,
            reasons=assessment.reasons,
            blocked_reason=f"Intent '{intent_name}' is not allowed for escalation.",
        )

    if not sensitivity.can_escalate_to_external(assessment.level, policy.escalation_allow_sensitive):
        return EscalationDecision(
            escalate=False,
            provider=policy.premium_provider,
            sensitivity_level=assessment.level,
            sensitivity_labels=assessment.labels,
            reasons=assessment.reasons,
            blocked_reason=f"Content classified as {assessment.level}; policy blocks external escalation.",
        )

    if user_requested_premium(message):
        reasons.append("User explicitly requested premium handling.")
    if intent_name in CRITICAL_INTENTS:
        reasons.append(f"Intent '{intent_name}' is treated as critical.")
    context_size = estimate_context_size(message, chunks)
    if context_size > settings.local_context_limit:
        reasons.append(
            f"Context size {context_size} exceeds local limit {settings.local_context_limit}."
        )
    if verdict and not verdict.approved:
        reasons.append("Verifier did not approve the local answer.")

    decision = bool(reasons)
    return EscalationDecision(
        escalate=decision,
        provider=policy.premium_provider,
        sensitivity_level=assessment.level,
        sensitivity_labels=assessment.labels,
        reasons=[*assessment.reasons, *reasons],
        blocked_reason=None if decision else "No escalation trigger matched.",
    )


def should_escalate(
    *,
    intent: Intent,
    message: str,
    verdict: VerifierVerdict | None,
    chunks: list[RetrievedChunk],
) -> bool:
    return escalation_decision(
        intent=intent,
        message=message,
        verdict=verdict,
        chunks=chunks,
    ).escalate
