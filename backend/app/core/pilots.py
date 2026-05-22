from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core import executive_proposals, opportunities
from app.core.db import db, dumps, init_db, loads, utc_now


PILOT_STATUSES = {"draft", "approved", "in_progress", "blocked", "completed", "cancelled"}
STATUS_TRANSITIONS = {
    "draft": {"approved", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"blocked", "completed", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class PilotTask(BaseModel):
    id: str
    title: str
    status: str = "open"
    owner: str = "Consultant"
    acceptance_criteria: list[str] = Field(default_factory=list)


class PilotProject(BaseModel):
    id: str
    tenant_id: str
    client_name: str
    source_type: str
    source_id: str | None = None
    title: str
    status: str
    owner: str
    start_date: str
    target_end_date: str
    success_metrics: list[str] = Field(default_factory=list)
    tasks: list[PilotTask] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


def create_pilot_from_proposal(
    *,
    proposal: executive_proposals.ExecutiveProposal,
    owner: str,
    target_end_date: str | None = None,
) -> PilotProject:
    now = utc_now()
    pilot = PilotProject(
        id=_pilot_id(proposal.tenant_id, proposal.selected_opportunity_id),
        tenant_id=proposal.tenant_id,
        client_name=proposal.client_name,
        source_type="executive_proposal",
        source_id=proposal.proposal_id,
        title=proposal.selected_opportunity_title,
        status="draft",
        owner=owner,
        start_date=now,
        target_end_date=target_end_date or _target_date(proposal.pilot_window),
        success_metrics=[
            f"Validate annual benefit potential of {proposal.annual_benefit_eur[0]}-{proposal.annual_benefit_eur[1]} EUR.",
            "Deliver a working pilot with human review before production use.",
            "Document privacy, runtime, and rollback decisions.",
        ],
        tasks=[
            PilotTask(
                id="scope",
                title="Confirm pilot scope and business owner",
                owner=owner,
                acceptance_criteria=[
                    "Pilot owner is named.",
                    "Target process and excluded processes are documented.",
                ],
            ),
            PilotTask(
                id="data",
                title="Confirm data sources and sensitivity level",
                owner="Technical operator",
                acceptance_criteria=[
                    "Required documents or systems are listed.",
                    "Sensitivity level is recorded before implementation.",
                ],
            ),
            PilotTask(
                id="prototype",
                title="Build first controlled prototype",
                owner="Implementation owner",
                acceptance_criteria=[
                    "Prototype runs on sample data.",
                    "Human review checkpoints are enforced.",
                ],
            ),
            PilotTask(
                id="measure",
                title="Measure outcome and decide rollout",
                owner=owner,
                acceptance_criteria=[
                    "Baseline and pilot metrics are compared.",
                    "Rollout, rollback, or stop decision is recorded.",
                ],
            ),
        ],
        risks=[proposal.primary_risk],
        created_at=now,
        updated_at=now,
    )
    return save_pilot(pilot)


def create_pilot_from_opportunity(
    *,
    tenant_id: str,
    client_name: str,
    diagnosis: opportunities.OpportunityDiagnosis,
    opportunity_id: str,
    owner: str,
    source_type: str = "diagnosis",
    source_id: str | None = None,
    target_end_date: str | None = None,
) -> PilotProject:
    opportunity = _find_opportunity(diagnosis, opportunity_id)
    now = utc_now()
    pilot = PilotProject(
        id=_pilot_id(tenant_id, opportunity.id),
        tenant_id=tenant_id,
        client_name=client_name,
        source_type=source_type,
        source_id=source_id or opportunity.id,
        title=opportunity.title,
        status="draft",
        owner=owner,
        start_date=now,
        target_end_date=target_end_date or _target_date(opportunity.recommended_phase),
        success_metrics=[
            f"Reduce manual effort or cost in {opportunity.area}.",
            f"Validate benefit estimate of {opportunity.annual_benefit_eur[0]}-{opportunity.annual_benefit_eur[1]} EUR.",
            "Confirm a go/no-go decision with measured evidence.",
        ],
        tasks=[
            PilotTask(
                id="scope",
                title="Lock pilot scope",
                owner=owner,
                acceptance_criteria=[
                    "Business process is named.",
                    "Success metrics are accepted by the client.",
                ],
            ),
            PilotTask(
                id="access",
                title="Prepare data and access",
                owner="Technical operator",
                acceptance_criteria=[
                    "Data sources are available.",
                    "Sensitive data handling is approved.",
                ],
            ),
            PilotTask(
                id="build",
                title="Build prototype",
                owner="Implementation owner",
                acceptance_criteria=[
                    "Prototype executes the first experiment.",
                    "Failure and rollback behavior is documented.",
                ],
            ),
            PilotTask(
                id="review",
                title="Review pilot evidence",
                owner=owner,
                acceptance_criteria=[
                    "Pilot metrics are compared with baseline.",
                    "Next action is approved.",
                ],
            ),
        ],
        risks=opportunity.risks,
        created_at=now,
        updated_at=now,
    )
    return save_pilot(pilot)


def save_pilot(pilot: PilotProject) -> PilotProject:
    init_db()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO pilot_projects (
                id, tenant_id, client_name, source_type, source_id, title, status,
                owner, start_date, target_end_date, success_metrics_json,
                tasks_json, risks_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pilot.id,
                pilot.tenant_id,
                pilot.client_name,
                pilot.source_type,
                pilot.source_id,
                pilot.title,
                pilot.status,
                pilot.owner,
                pilot.start_date,
                pilot.target_end_date,
                dumps(pilot.success_metrics),
                dumps([task.model_dump() for task in pilot.tasks]),
                dumps(pilot.risks),
                pilot.created_at,
                pilot.updated_at,
            ),
        )
    return pilot


def list_pilots(tenant_id: str, status: str | None = None) -> list[PilotProject]:
    init_db()
    query = "SELECT * FROM pilot_projects WHERE tenant_id = ?"
    params: list[str] = [tenant_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_pilot(row) for row in rows]


def get_pilot(tenant_id: str, pilot_id: str) -> PilotProject | None:
    init_db()
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM pilot_projects WHERE tenant_id = ? AND id = ?",
            (tenant_id, pilot_id),
        ).fetchone()
    return _row_to_pilot(row) if row else None


def update_pilot_status(
    *,
    tenant_id: str,
    pilot_id: str,
    status: str,
) -> PilotProject:
    if status not in PILOT_STATUSES:
        raise ValueError(f"Unknown pilot status: {status}")
    pilot = get_pilot(tenant_id, pilot_id)
    if not pilot:
        raise KeyError(pilot_id)
    if status != pilot.status and status not in STATUS_TRANSITIONS[pilot.status]:
        raise ValueError(f"Invalid transition from {pilot.status} to {status}")
    updated_at = utc_now()
    with db() as conn:
        conn.execute(
            "UPDATE pilot_projects SET status = ?, updated_at = ? WHERE tenant_id = ? AND id = ?",
            (status, updated_at, tenant_id, pilot_id),
        )
    updated = get_pilot(tenant_id, pilot_id)
    if not updated:
        raise KeyError(pilot_id)
    return updated


def complete_task(
    *,
    tenant_id: str,
    pilot_id: str,
    task_id: str,
) -> PilotProject:
    pilot = get_pilot(tenant_id, pilot_id)
    if not pilot:
        raise KeyError(pilot_id)
    changed = False
    tasks: list[PilotTask] = []
    for task in pilot.tasks:
        if task.id == task_id:
            tasks.append(task.model_copy(update={"status": "completed"}))
            changed = True
        else:
            tasks.append(task)
    if not changed:
        raise KeyError(task_id)
    updated_at = utc_now()
    with db() as conn:
        conn.execute(
            "UPDATE pilot_projects SET tasks_json = ?, updated_at = ? WHERE tenant_id = ? AND id = ?",
            (dumps([task.model_dump() for task in tasks]), updated_at, tenant_id, pilot_id),
        )
    updated = get_pilot(tenant_id, pilot_id)
    if not updated:
        raise KeyError(pilot_id)
    return updated


def _find_opportunity(
    diagnosis: opportunities.OpportunityDiagnosis,
    opportunity_id: str,
) -> opportunities.Opportunity:
    for opportunity in diagnosis.top_opportunities:
        if opportunity.id == opportunity_id:
            return opportunity
    raise KeyError(opportunity_id)


def _row_to_pilot(row) -> PilotProject:
    return PilotProject(
        id=row["id"],
        tenant_id=row["tenant_id"],
        client_name=row["client_name"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        title=row["title"],
        status=row["status"],
        owner=row["owner"],
        start_date=row["start_date"],
        target_end_date=row["target_end_date"],
        success_metrics=loads(row["success_metrics_json"], []),
        tasks=[PilotTask(**item) for item in loads(row["tasks_json"], [])],
        risks=loads(row["risks_json"], []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _pilot_id(tenant_id: str, opportunity_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tenant = _slug(tenant_id)
    safe_opportunity = _slug(opportunity_id)
    return f"{stamp}-{safe_tenant}-{safe_opportunity}-{uuid4().hex[:8]}"


def _target_date(window: str) -> str:
    days = 30
    lowered = window.lower()
    if "6-10" in lowered:
        days = 70
    elif "4-6" in lowered:
        days = 42
    elif "week 9" in lowered or "deployment" in lowered:
        days = 90
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")[:48]
