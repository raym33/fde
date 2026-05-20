from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.labs.service import LabsService


router = APIRouter(prefix="/labs", tags=["labs"])
service = LabsService()


class RunExperimentRequest(BaseModel):
    lab_id: Optional[str] = None
    triggered_by: str = "api"


class ReportDecisionRequest(BaseModel):
    decision: str
    decided_by: str = "admin"
    notes: str = ""


class ApplyChangeRequest(BaseModel):
    applied_by: str = "admin"


@router.get("/catalog")
def catalog() -> dict:
    return {"labs": service.list_catalog()}


@router.get("/schedule/preview")
def schedule_preview() -> dict:
    return {"schedule": service.schedule_preview()}


@router.post("/experiments/run")
def run_experiment(payload: RunExperimentRequest) -> dict:
    try:
        return service.run_experiment(lab_id=payload.lab_id, triggered_by=payload.triggered_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports")
def reports(status: Optional[str] = None) -> dict:
    return {"reports": service.list_reports(status=status)}


@router.get("/changes")
def changes(status: Optional[str] = None) -> dict:
    return {"changes": service.list_changes(status=status)}


@router.get("/feature-flags")
def feature_flags() -> dict:
    return {"feature_flags": service.feature_flags()}


@router.get("/runs")
def runs(limit: int = 20) -> dict:
    return {"runs": service.list_runs(limit=limit)}


@router.get("/changes/{change_id}")
def change_detail(change_id: str) -> dict:
    change = service.get_change(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    return change


@router.post("/changes/{change_id}/apply")
def apply_change(change_id: str, payload: ApplyChangeRequest) -> dict:
    try:
        return service.apply_change(change_id, applied_by=payload.applied_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports/{report_id}")
def report_detail(report_id: str) -> dict:
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports/{report_id}/decision")
def decide_report(report_id: str, payload: ReportDecisionRequest) -> dict:
    try:
        return service.decide_report(
            report_id=report_id,
            decision=payload.decision,
            decided_by=payload.decided_by,
            notes=payload.notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
