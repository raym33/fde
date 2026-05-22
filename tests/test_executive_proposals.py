from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core import executive_proposals, opportunities
from app.main import app


def _build_diagnosis() -> opportunities.OpportunityDiagnosis:
    return opportunities.diagnose_opportunities(
        "Where should we implement AI first in an SME with repetitive support, invoices, and internal document search?",
        [],
        client_name="Demo SL",
        employee_count=180,
        top_k=5,
    )


def test_build_and_persist_executive_proposal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(executive_proposals, "DEFAULT_OUTPUT_DIR", tmp_path)
    diagnosis = _build_diagnosis()

    proposal = executive_proposals.build_proposal(
        tenant_id="demo-tenant",
        client_name="Demo SL",
        diagnosis=diagnosis,
    )
    artifacts = executive_proposals.persist_proposal(proposal)

    assert proposal.selected_opportunity_title
    assert proposal.sales_message
    assert Path(artifacts["json_path"]).exists()
    assert Path(artifacts["html_path"]).exists()
    assert "Executive AI Proposal" in Path(artifacts["html_path"]).read_text(encoding="utf-8")


def test_executive_proposal_route(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(executive_proposals, "DEFAULT_OUTPUT_DIR", tmp_path)
    diagnosis = _build_diagnosis()
    client = TestClient(app)
    headers = {
        "X-Tenant-Id": "proposal-tenant",
        "X-User-Id": "tester",
        "X-Client-Name": "Proposal Tenant SL",
    }

    response = client.post(
        "/opportunities/executive-proposal",
        headers=headers,
        json={
          "diagnosis": diagnosis.model_dump(),
          "opportunity_id": diagnosis.top_opportunities[0].id,
          "persist": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal"]["selected_opportunity_id"] == diagnosis.top_opportunities[0].id
    assert payload["artifacts"]["html_path"].endswith("proposal.html")
    assert "Executive AI Proposal" in payload["html"]
