from __future__ import annotations

from pathlib import Path

from app.core import implementation_engine, opportunities


def test_generate_bundle_from_opportunity(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(implementation_engine, "DEFAULT_OUTPUT_DIR", tmp_path)

    diagnosis = opportunities.diagnose_opportunities(
        "Where should we implement AI first in an SME with repetitive support tickets and FAQs?",
        [],
        client_name="Demo SL",
        employee_count=120,
        top_k=5,
    )
    opportunity = next(item for item in diagnosis.top_opportunities if item.id == "support_knowledge_agent")

    bundle = implementation_engine.generate_bundle(
        tenant_id="demo-tenant",
        client_name="Demo SL",
        diagnosis=diagnosis,
        opportunity=opportunity,
        review=True,
    )

    output_dir = Path(bundle["output_dir"])
    assert output_dir.exists()
    assert (output_dir / "swarm_input.md").exists()
    assert (output_dir / "execution_request.json").exists()
    assert (output_dir / "review_checklist.md").exists()
    assert bundle["external_execution"]["executed"] is False
