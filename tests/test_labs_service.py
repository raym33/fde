from __future__ import annotations

from app.config import get_settings
from app.core.db import init_db
from app.labs.service import LabsService


def _init_temp_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LABS_SQLITE_PATH", str(tmp_path / "labs.sqlite3"))
    get_settings.cache_clear()
    init_db()


def test_service_records_runs_and_reports(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    service = LabsService()

    result = service.run_experiment(triggered_by="pytest")

    assert len(result["runs"]) == 6
    assert {run["status"] for run in result["runs"]} <= {
        "report_proposed",
        "no_material_improvement",
        "failed",
    }
    assert not any(run["status"] == "failed" for run in result["runs"])
    assert len(service.list_runs(limit=10)) == 6
    assert len(service.list_reports(status="proposed")) == len(result["reports"])


def test_report_decision_flow_stages_and_applies_change(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    service = LabsService()
    result = service.run_experiment("model_routing_cost", triggered_by="pytest")

    assert result["reports"], "model_routing_cost should produce a report"
    report_id = result["reports"][0]["id"]

    approved = service.decide_report(
        report_id,
        decision="approve",
        decided_by="pytest",
        notes="Approved in unit test.",
    )
    assert approved["status"] == "approved"
    assert approved["change"]["status"] == "staged"

    applied = service.apply_change(approved["change"]["id"], applied_by="pytest")
    assert applied["status"] == "applied"

    implemented = service.get_report(report_id)
    assert implemented is not None
    assert implemented["status"] == "implemented"


def test_failed_lab_is_recorded_without_crashing_batch(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)

    from app.labs import registry
    from app.labs.base import BaseLab

    class BrokenLab(BaseLab):
        def run(self):
            raise RuntimeError("intentional lab failure")

        def build_report(self, result):
            raise AssertionError("should not be called")

    original = registry.LAB_CLASSES["rag_grounding"]
    monkeypatch.setitem(registry.LAB_CLASSES, "rag_grounding", BrokenLab)
    try:
        service = LabsService()
        result = service.run_experiment(triggered_by="pytest")
    finally:
        monkeypatch.setitem(registry.LAB_CLASSES, "rag_grounding", original)

    failed = [run for run in result["runs"] if run["lab_id"] == "rag_grounding"]
    assert len(failed) == 1
    assert failed[0]["status"] == "failed"
    assert failed[0]["metrics"]["error_type"] == "RuntimeError"
    assert len(result["runs"]) == 6
