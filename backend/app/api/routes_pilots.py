from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import executive_proposals, opportunities, pilots
from app.deps import Principal, get_principal

router = APIRouter(prefix="/pilots", tags=["pilots"])


class CreatePilotRequest(BaseModel):
    source_type: str = "diagnosis"
    source_id: str | None = None
    diagnosis: opportunities.OpportunityDiagnosis | None = None
    opportunity_id: str | None = None
    proposal: executive_proposals.ExecutiveProposal | None = None
    owner: str | None = None
    target_end_date: str | None = None


class UpdatePilotStatusRequest(BaseModel):
    status: str


@router.post("")
async def create_pilot(
    body: CreatePilotRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    owner = body.owner or principal.user_id
    try:
        if body.proposal:
            pilot = pilots.create_pilot_from_proposal(
                proposal=body.proposal,
                owner=owner,
                target_end_date=body.target_end_date,
            )
        elif body.diagnosis and body.opportunity_id:
            pilot = pilots.create_pilot_from_opportunity(
                tenant_id=principal.tenant_id,
                client_name=principal.client_name,
                diagnosis=body.diagnosis,
                opportunity_id=body.opportunity_id,
                owner=owner,
                source_type=body.source_type,
                source_id=body.source_id,
                target_end_date=body.target_end_date,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide either a proposal or a diagnosis with opportunity_id.",
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Source item not found: {exc}") from exc
    return {"pilot": pilot.model_dump()}


@router.get("")
async def list_pilots(
    status: str | None = None,
    principal: Principal = Depends(get_principal),
) -> dict:
    return {
        "pilots": [
            pilot.model_dump()
            for pilot in pilots.list_pilots(principal.tenant_id, status=status)
        ]
    }


@router.get("/{pilot_id}")
async def get_pilot(
    pilot_id: str,
    principal: Principal = Depends(get_principal),
) -> dict:
    pilot = pilots.get_pilot(principal.tenant_id, pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return {"pilot": pilot.model_dump()}


@router.post("/{pilot_id}/status")
async def update_pilot_status(
    pilot_id: str,
    body: UpdatePilotStatusRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        pilot = pilots.update_pilot_status(
            tenant_id=principal.tenant_id,
            pilot_id=pilot_id,
            status=body.status,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pilot not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"pilot": pilot.model_dump()}


@router.post("/{pilot_id}/tasks/{task_id}/complete")
async def complete_pilot_task(
    pilot_id: str,
    task_id: str,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        pilot = pilots.complete_task(
            tenant_id=principal.tenant_id,
            pilot_id=pilot_id,
            task_id=task_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Pilot or task not found: {exc}") from exc
    return {"pilot": pilot.model_dump()}
