from __future__ import annotations

from app.labs.catalog import LAB_DEFINITIONS
from scripts.labs_quality_gate import validate_all_labs


def test_labs_quality_gate_passes_for_all_catalog_labs() -> None:
    summaries = validate_all_labs()

    assert len(summaries) == len(LAB_DEFINITIONS)
    assert {row["lab_id"] for row in summaries} == {lab.id for lab in LAB_DEFINITIONS}
    assert all(0 <= row["baseline_score"] <= 100 for row in summaries)
    assert all(0 <= row["new_score"] <= 100 for row in summaries)
