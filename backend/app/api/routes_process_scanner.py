"""Endpoints for the AI Implementation Scanner."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core import process_scanner
from app.deps import Principal, get_principal

router = APIRouter(prefix="/process-scanner", tags=["process-scanner"])


@router.post("/analyze")
async def analyze_process(
    body: process_scanner.ProcessScannerRequest,
    _principal: Principal = Depends(get_principal),
) -> dict:
    try:
        result = process_scanner.scan_processes(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "result": result.model_dump(),
        "markdown": process_scanner.render_markdown(result),
    }
