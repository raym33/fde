from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.core import executive_proposals, opportunities, pilots
from app.core.db import init_db
from app.main import app


def _use_temp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LABS_SQLITE_PATH", str(tmp_path / "pilots.sqlite3"))
    get_settings.cache_clear()
    init_db()


def _diagnosis() -> opportunities.OpportunityDiagnosis:
    return opportunities.diagnose_opportunities(
        "Where should we implement AI first in an SME with repetitive support, invoices, and internal documents?",
        [],
        client_name="Pilot SL",
        employee_count=80,
        top_k=5,
    )


def test_create_and_progress_pilot_from_opportunity(monkeypatch, tmp_path: Path) -> None:
    _use_temp_db(monkeypatch, tmp_path)
    diagnosis = _diagnosis()
    opportunity = diagnosis.top_opportunities[0]

    pilot = pilots.create_pilot_from_opportunity(
        tenant_id="pilot-tenant",
        client_name="Pilot SL",
        diagnosis=diagnosis,
        opportunity_id=opportunity.id,
        owner="consultant",
    )

    assert pilot.status == "draft"
    assert pilot.tasks
    assert pilot.success_metrics

    approved = pilots.update_pilot_status(
        tenant_id="pilot-tenant",
        pilot_id=pilot.id,
        status="approved",
    )
    assert approved.status == "approved"

    progressed = pilots.complete_task(
        tenant_id="pilot-tenant",
        pilot_id=pilot.id,
        task_id=pilot.tasks[0].id,
    )
    assert progressed.tasks[0].status == "completed"


def test_invalid_pilot_transition_is_rejected(monkeypatch, tmp_path: Path) -> None:
    _use_temp_db(monkeypatch, tmp_path)
    proposal = executive_proposals.build_proposal(
        tenant_id="pilot-tenant",
        client_name="Pilot SL",
        diagnosis=_diagnosis(),
    )
    pilot = pilots.create_pilot_from_proposal(proposal=proposal, owner="consultant")

    try:
        pilots.update_pilot_status(
            tenant_id="pilot-tenant",
            pilot_id=pilot.id,
            status="completed",
        )
    except ValueError as exc:
        assert "Invalid transition" in str(exc)
    else:
        raise AssertionError("Invalid transition was accepted")


def test_pilot_routes(monkeypatch, tmp_path: Path) -> None:
    _use_temp_db(monkeypatch, tmp_path)
    diagnosis = _diagnosis()
    opportunity = diagnosis.top_opportunities[0]
    client = TestClient(app)
    headers = {
        "X-Tenant-Id": "pilot-route-tenant",
        "X-User-Id": "consultant",
        "X-Client-Name": "Pilot Route SL",
    }

    create_response = client.post(
        "/pilots",
        headers=headers,
        json={
            "diagnosis": diagnosis.model_dump(),
            "opportunity_id": opportunity.id,
            "owner": "consultant",
        },
    )

    assert create_response.status_code == 200
    pilot = create_response.json()["pilot"]
    assert pilot["source_type"] == "diagnosis"
    assert pilot["status"] == "draft"

    list_response = client.get("/pilots", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["pilots"]) == 1

    status_response = client.post(
        f"/pilots/{pilot['id']}/status",
        headers=headers,
        json={"status": "approved"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["pilot"]["status"] == "approved"

    task_id = pilot["tasks"][0]["id"]
    task_response = client.post(
        f"/pilots/{pilot['id']}/tasks/{task_id}/complete",
        headers=headers,
    )
    assert task_response.status_code == 200
    assert task_response.json()["pilot"]["tasks"][0]["status"] == "completed"
