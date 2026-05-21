"""Quality gate for FDE Labs.

This script is intentionally stricter than the smoke test:

- every catalog lab must be registered;
- every lab must be deterministic across two consecutive runs;
- score and metrics payloads must be valid;
- every material improvement must produce a reviewable Core Report draft.

It does not mutate the labs database.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.labs.catalog import LAB_DEFINITIONS
from app.labs.registry import LAB_CLASSES, make_lab
from app.labs.schemas import CoreReportDraft, LabRunResult


ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _validate_result(lab_id: str, result: LabRunResult, errors: list[str]) -> None:
    _assert(result.lab_id == lab_id, f"{lab_id}: result.lab_id mismatch", errors)
    _assert(0 <= result.baseline_score <= 100, f"{lab_id}: baseline_score outside 0-100", errors)
    _assert(0 <= result.new_score <= 100, f"{lab_id}: new_score outside 0-100", errors)
    _assert(result.threshold_pct >= 0, f"{lab_id}: threshold_pct must be non-negative", errors)
    _assert(isinstance(result.metrics, dict) and bool(result.metrics), f"{lab_id}: empty metrics", errors)
    _assert("baseline" in result.metrics, f"{lab_id}: metrics missing baseline", errors)
    _assert("candidate" in result.metrics, f"{lab_id}: metrics missing candidate", errors)
    _assert(result.notes.strip() != "", f"{lab_id}: notes should explain the experiment", errors)


def _validate_report(lab_id: str, report: CoreReportDraft, errors: list[str]) -> None:
    _assert(report.lab_id == lab_id, f"{lab_id}: report.lab_id mismatch", errors)
    for field in ("title", "summary", "recommendation", "rollout_plan", "rollback_plan"):
        value = getattr(report, field)
        _assert(isinstance(value, str) and value.strip() != "", f"{lab_id}: report {field} empty", errors)
    _assert(report.risk_level in ALLOWED_RISK_LEVELS, f"{lab_id}: invalid risk_level", errors)
    _assert(report.status == "proposed", f"{lab_id}: report must start as proposed", errors)
    _assert(bool(report.evidence), f"{lab_id}: report evidence empty", errors)
    _assert(isinstance(report.metrics, dict) and bool(report.metrics), f"{lab_id}: report metrics empty", errors)


def validate_all_labs() -> list[dict[str, Any]]:
    errors: list[str] = []
    catalog_ids = [lab.id for lab in LAB_DEFINITIONS]
    registered_ids = list(LAB_CLASSES.keys())
    _assert(set(catalog_ids) == set(registered_ids), "catalog and registry ids differ", errors)

    summaries: list[dict[str, Any]] = []
    for lab_id in catalog_ids:
        first_lab = make_lab(lab_id)
        second_lab = make_lab(lab_id)
        first = first_lab.run()
        second = second_lab.run()

        _validate_result(lab_id, first, errors)
        _validate_result(lab_id, second, errors)
        _assert(
            _canonical(first.metrics) == _canonical(second.metrics)
            and first.baseline_score == second.baseline_score
            and first.new_score == second.new_score,
            f"{lab_id}: lab run is not deterministic",
            errors,
        )

        report_status = "not_required"
        if first.produces_report:
            report = first_lab.build_report(first)
            _validate_report(lab_id, report, errors)
            report_status = "valid_report"

        summaries.append(
            {
                "lab_id": lab_id,
                "baseline_score": first.baseline_score,
                "new_score": first.new_score,
                "improvement_pct": round(first.improvement_pct, 2),
                "threshold_pct": first.threshold_pct,
                "produces_report": first.produces_report,
                "report_status": report_status,
            }
        )

    if errors:
        raise AssertionError("\n".join(errors))
    return summaries


def main() -> None:
    summaries = validate_all_labs()
    print("Labs quality gate: OK")
    for row in summaries:
        print(
            f"- {row['lab_id']}: {row['baseline_score']} -> {row['new_score']} "
            f"({row['improvement_pct']}%), report={row['report_status']}"
        )


if __name__ == "__main__":
    main()
