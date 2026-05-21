from __future__ import annotations

from pathlib import Path

from app.core import implementation_engine, opportunities


def _diagnosis_for(question: str) -> opportunities.OpportunityDiagnosis:
    return opportunities.diagnose_opportunities(
        question,
        [],
        client_name="Demo SL",
        employee_count=250,
        top_k=8,
    )


def test_generate_bundle_uses_document_search_template(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(implementation_engine, "DEFAULT_OUTPUT_DIR", tmp_path)
    diagnosis = _diagnosis_for("We need internal document search over contracts, policies, and procedures.")
    opportunity = next(item for item in diagnosis.top_opportunities if item.id == "document_search_copilot")

    bundle = implementation_engine.generate_bundle(
        tenant_id="demo-tenant",
        client_name="Demo SL",
        diagnosis=diagnosis,
        opportunity=opportunity,
        review=True,
    )

    assert bundle["service_file"].endswith("document-search-copilot.md")


def test_generate_bundle_uses_invoice_template(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(implementation_engine, "DEFAULT_OUTPUT_DIR", tmp_path)
    diagnosis = _diagnosis_for("We process supplier invoices manually and need finance automation.")
    opportunity = next(item for item in diagnosis.top_opportunities if item.id == "finance_invoice_automation")

    bundle = implementation_engine.generate_bundle(
        tenant_id="demo-tenant",
        client_name="Demo SL",
        diagnosis=diagnosis,
        opportunity=opportunity,
        review=True,
    )

    assert bundle["service_file"].endswith("invoice-automation.md")


def test_generate_bundle_uses_governance_template(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(implementation_engine, "DEFAULT_OUTPUT_DIR", tmp_path)
    diagnosis = _diagnosis_for("We need an AI governance roadmap, risk policy, and executive portfolio.")
    opportunity = next(item for item in diagnosis.top_opportunities if item.id == "executive_ai_governance")

    bundle = implementation_engine.generate_bundle(
        tenant_id="demo-tenant",
        client_name="Demo SL",
        diagnosis=diagnosis,
        opportunity=opportunity,
        review=True,
    )

    assert bundle["service_file"].endswith("ai-governance-rollout.md")
