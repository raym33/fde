from __future__ import annotations

from app.core.schemas import RetrievedChunk
from app.security import sensitivity


def test_classify_regulated_when_health_and_pii_present() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            text="Historia clínica del paciente con email maria@example.com y diagnostico reciente.",
            score=1.0,
            metadata={},
        )
    ]
    assessment = sensitivity.classify_sensitivity("Review this clinic workflow", chunks)
    assert assessment.level == "regulated"
    assert "pii" in assessment.labels
    assert any("health data" in reason for reason in assessment.reasons)


def test_classify_confidential_for_contract_and_invoice_content() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            text="Supplier invoice and contract terms for ERP validation.",
            score=1.0,
            metadata={},
        )
    ]
    assessment = sensitivity.classify_sensitivity("Need automation for invoice processing", chunks)
    assert assessment.level == "confidential"
    assert "confidential" in assessment.labels


def test_classify_internal_for_policy_without_sensitive_markers() -> None:
    assessment = sensitivity.classify_sensitivity(
        "Summarise the internal policy and procedure manual for onboarding.",
        [],
    )
    assert assessment.level == "internal"


def test_can_escalate_only_public_or_internal_by_default() -> None:
    assert sensitivity.can_escalate_to_external("public", False) is True
    assert sensitivity.can_escalate_to_external("internal", False) is True
    assert sensitivity.can_escalate_to_external("confidential", False) is False
    assert sensitivity.can_escalate_to_external("regulated", False) is False
