from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.opportunities import Opportunity, OpportunityDiagnosis


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "executive_proposals"


class ExecutiveProposal(BaseModel):
    proposal_id: str
    created_at: str
    tenant_id: str
    client_name: str
    company_size: str
    question: str
    selected_opportunity_id: str
    selected_opportunity_title: str
    problem_statement: str
    recommended_solution: str
    annual_benefit_eur: tuple[int, int]
    setup_cost_eur: tuple[int, int]
    monthly_cost_eur: tuple[int, int]
    deployment_mode: str
    pilot_window: str
    first_step: str
    primary_risk: str
    quick_wins: list[str] = Field(default_factory=list)
    strategic_bets: list[str] = Field(default_factory=list)
    roadmap_90_days: list[dict] = Field(default_factory=list)
    sales_message: str


def build_proposal(
    *,
    tenant_id: str,
    client_name: str,
    diagnosis: OpportunityDiagnosis,
    selected_opportunity_id: str | None = None,
) -> ExecutiveProposal:
    selected = _pick_selected_opportunity(diagnosis, selected_opportunity_id)
    proposal_id = _proposal_id(tenant_id, selected.id)
    return ExecutiveProposal(
        proposal_id=proposal_id,
        created_at=_now(),
        tenant_id=tenant_id,
        client_name=client_name,
        company_size=diagnosis.company_size,
        question=diagnosis.question,
        selected_opportunity_id=selected.id,
        selected_opportunity_title=selected.title,
        problem_statement=selected.problem,
        recommended_solution=selected.ai_solution,
        annual_benefit_eur=selected.annual_benefit_eur,
        setup_cost_eur=selected.setup_cost_eur,
        monthly_cost_eur=selected.monthly_cost_eur,
        deployment_mode=_deployment_mode(diagnosis, selected),
        pilot_window=_pilot_window(selected),
        first_step=selected.first_experiment,
        primary_risk=(selected.risks or ["No principal risk defined"])[0],
        quick_wins=_map_ids_to_titles(diagnosis.quick_wins, diagnosis),
        strategic_bets=_map_ids_to_titles(diagnosis.strategic_bets, diagnosis),
        roadmap_90_days=diagnosis.roadmap_90_days,
        sales_message=(
            f"{client_name} should start with {selected.title.lower()} because it combines clear business value, "
            f"measurable ROI, and a pilot that can launch in {_pilot_window(selected).lower()}."
        ),
    )


def persist_proposal(
    proposal: ExecutiveProposal,
    *,
    output_dir: Path | None = None,
) -> dict:
    base_dir = output_dir or DEFAULT_OUTPUT_DIR
    proposal_dir = base_dir / proposal.proposal_id
    proposal_dir.mkdir(parents=True, exist_ok=True)

    json_path = proposal_dir / "proposal.json"
    html_path = proposal_dir / "proposal.html"

    json_path.write_text(
        json.dumps(proposal.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    html_path.write_text(render_proposal_html(proposal), encoding="utf-8")
    return {
        "output_dir": str(proposal_dir),
        "json_path": str(json_path),
        "html_path": str(html_path),
    }


def render_proposal_html(proposal: ExecutiveProposal) -> str:
    quick_wins = "".join(f"<li>{_escape(item)}</li>" for item in proposal.quick_wins) or "<li>No quick wins defined.</li>"
    strategic = "".join(f"<li>{_escape(item)}</li>" for item in proposal.strategic_bets) or "<li>No strategic bets defined.</li>"
    roadmap = "".join(
        f"<li><strong>{_escape(item.get('name', 'Phase'))}</strong> — {_escape(item.get('deliverable', ''))}</li>"
        for item in proposal.roadmap_90_days[:3]
    ) or "<li>No roadmap defined.</li>"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{_escape(proposal.client_name)} — Executive AI Proposal</title>
    <style>
      body {{ font-family: Inter, Arial, sans-serif; margin: 32px; color: #1e2426; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      .eyebrow {{ text-transform: uppercase; color: #176a63; font-size: 12px; font-weight: 800; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
      .card {{ border: 1px solid #d8e1dd; padding: 16px; background: #fff; }}
      .wide {{ grid-column: 1 / -1; }}
      ul {{ margin: 0; padding-left: 18px; }}
      li {{ margin-bottom: 6px; line-height: 1.5; }}
      @media print {{ body {{ margin: 16px; }} }}
    </style>
  </head>
  <body>
    <p class="eyebrow">Executive AI proposal</p>
    <h1>{_escape(proposal.client_name)}</h1>
    <p>{_escape(proposal.sales_message)}</p>
    <div class="grid">
      <section class="card">
        <h2>Priority problem</h2>
        <p>{_escape(proposal.problem_statement)}</p>
      </section>
      <section class="card">
        <h2>Recommended initiative</h2>
        <p>{_escape(proposal.selected_opportunity_title)}</p>
      </section>
      <section class="card">
        <h2>Financial profile</h2>
        <p>Annual benefit: {_eur_range(proposal.annual_benefit_eur)}</p>
        <p>Initial setup: {_eur_range(proposal.setup_cost_eur)}</p>
        <p>Monthly run cost: {_eur_range(proposal.monthly_cost_eur)}</p>
      </section>
      <section class="card">
        <h2>Delivery mode</h2>
        <p>{_escape(proposal.deployment_mode)}</p>
        <p>First pilot: {_escape(proposal.pilot_window)}</p>
      </section>
      <section class="card wide">
        <h2>Quick wins</h2>
        <ul>{quick_wins}</ul>
      </section>
      <section class="card wide">
        <h2>90-day roadmap</h2>
        <ul>{roadmap}</ul>
      </section>
      <section class="card">
        <h2>Main risk</h2>
        <p>{_escape(proposal.primary_risk)}</p>
      </section>
      <section class="card">
        <h2>Next step</h2>
        <p>{_escape(proposal.first_step)}</p>
      </section>
      <section class="card wide">
        <h2>Strategic bets</h2>
        <ul>{strategic}</ul>
      </section>
    </div>
  </body>
</html>
"""


def _pick_selected_opportunity(
    diagnosis: OpportunityDiagnosis,
    selected_opportunity_id: str | None,
) -> Opportunity:
    if selected_opportunity_id:
        for item in diagnosis.top_opportunities:
            if item.id == selected_opportunity_id:
                return item
    return diagnosis.top_opportunities[0]


def _map_ids_to_titles(ids: list[str], diagnosis: OpportunityDiagnosis) -> list[str]:
    items = {item.id: item.title for item in diagnosis.top_opportunities}
    return [items.get(item_id, item_id) for item_id in ids]


def _deployment_mode(diagnosis: OpportunityDiagnosis, selected: Opportunity) -> str:
    lowered = f"{diagnosis.question} {' '.join(selected.risks)} {' '.join(selected.data_needed)}".lower()
    if any(token in lowered for token in {"clinic", "clínica", "legal", "gdpr", "rgpd", "contract", "contrato", "patient", "paciente"}):
        return "Local-first with tightly controlled hybrid escalation"
    if any(token in lowered for token in {"document", "documento", "invoice", "factura", "erp", "crm"}):
        return "Hybrid with local retrieval over internal data"
    return "Cloud or hybrid depending on latency, privacy, and operating cost"


def _pilot_window(selected: Opportunity) -> str:
    effort = selected.score.effort
    if effort <= 2:
        return "2-4 weeks"
    if effort == 3:
        return "4-6 weeks"
    return "6-10 weeks"


def _proposal_id(tenant_id: str, opportunity_id: str) -> str:
    safe_tenant = tenant_id.replace("/", "-").replace(" ", "-")
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{safe_tenant}-{opportunity_id}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eur_range(values: tuple[int, int]) -> str:
    return f"{values[0]:,}–{values[1]:,} EUR"


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
