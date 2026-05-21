"""Endpoints for AI opportunity discovery."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import implementation_engine
from app.core import opportunities
from app.deps import Principal, get_principal
from app.knowledge.updates import retrieve_knowledge
from app.rag.retriever import retrieve

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class OpportunityDiagnosisRequest(BaseModel):
    question: str
    employee_count: int | None = None
    top_k: int = 8


class OpportunityBundleRequest(BaseModel):
    question: str
    opportunity_id: str
    employee_count: int | None = None
    top_k: int = 8
    review: bool = True


@router.post("/diagnose")
async def diagnose(
    body: OpportunityDiagnosisRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    """Return a structured opportunity map for a client's company."""
    chunks = await retrieve(
        query=body.question,
        tenant_id=principal.tenant_id,
        top_k=8,
    )
    platform_chunks = retrieve_knowledge(body.question, top_k=4)
    diagnosis = opportunities.diagnose_opportunities(
        body.question,
        [*platform_chunks, *chunks],
        client_name=principal.client_name,
        employee_count=body.employee_count,
        top_k=body.top_k,
    )
    return {
        "diagnosis": diagnosis.model_dump(),
        "markdown": opportunities.render_markdown(diagnosis),
    }


@router.post("/implementation-bundle")
async def create_implementation_bundle(
    body: OpportunityBundleRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    chunks = await retrieve(
        query=body.question,
        tenant_id=principal.tenant_id,
        top_k=8,
    )
    platform_chunks = retrieve_knowledge(body.question, top_k=4)
    diagnosis = opportunities.diagnose_opportunities(
        body.question,
        [*platform_chunks, *chunks],
        client_name=principal.client_name,
        employee_count=body.employee_count,
        top_k=body.top_k,
    )
    opportunity = next((item for item in diagnosis.top_opportunities if item.id == body.opportunity_id), None)
    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail=f"Opportunity '{body.opportunity_id}' was not found in the current diagnosis set.",
        )

    bundle = implementation_engine.generate_bundle(
        tenant_id=principal.tenant_id,
        client_name=principal.client_name,
        diagnosis=diagnosis,
        opportunity=opportunity,
        review=body.review,
    )
    return {
        "opportunity": opportunity.model_dump(),
        "bundle": bundle,
    }
