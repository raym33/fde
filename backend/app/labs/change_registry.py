from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.core.db import db, dumps, loads, utc_now


@dataclass(frozen=True)
class ChangeTemplate:
    target_type: str
    target_key: str
    feature_flag: str
    payload: dict[str, Any]
    rollback: dict[str, Any]


CHANGE_TEMPLATES: dict[str, ChangeTemplate] = {
    "rag_grounding": ChangeTemplate(
        target_type="rag_policy",
        target_key="retrieval.hybrid_citation_gate",
        feature_flag="rag.hybrid_citation_gate.v1",
        payload={
            "retrieval": "hybrid_bm25_vector",
            "citation_gate": True,
            "tenant_filter_required": True,
            "rollout_scope": "pilot_tenants",
        },
        rollback={"retrieval": "vector_only", "citation_gate": False},
    ),
    "model_routing_cost": ChangeTemplate(
        target_type="model_router_policy",
        target_key="router.premium_escalation_v2",
        feature_flag="router.premium_escalation.v2",
        payload={
            "cheap_first_pass": True,
            "premium_only_for": ["grc", "deliverable", "high_risk_strategy"],
            "max_quality_drop_points": 0,
        },
        rollback={"cheap_first_pass": False, "premium_only_for": ["grc", "deliverable"]},
    ),
    "agent_workflow": ChangeTemplate(
        target_type="orchestration_policy",
        target_key="workflow.bounded_planner_verifier",
        feature_flag="workflow.bounded_planner_verifier.v1",
        payload={
            "planner": True,
            "verifier": True,
            "max_retry_budget": 2,
            "tool_failure_recovery": True,
        },
        rollback={"planner": False, "max_retry_budget": 0},
    ),
    "roi_solutions": ChangeTemplate(
        target_type="solutions_policy",
        target_key="scoring.spanish_sme_budget_profiles",
        feature_flag="solutions.spanish_sme_budget_profiles.v1",
        payload={
            "budget_profiles": ["low_budget_spain", "mid_market_spain"],
            "conservative_payback_bands": True,
            "vertical_tags_required": True,
        },
        rollback={"budget_profiles": ["default"], "conservative_payback_bands": False},
    ),
    "grc_eu_ai_act": ChangeTemplate(
        target_type="workflow_policy",
        target_key="eu_ai_act.role_specific_controls",
        feature_flag="grc.eu_ai_act.role_specific_controls.v1",
        payload={
            "ask_client_role_first": True,
            "roles": ["provider", "deployer", "importer", "distributor"],
            "legal_disclaimer_required": True,
            "source_citations_required": True,
        },
        rollback={"ask_client_role_first": False, "roles": ["deployer"]},
    ),
    "market_intelligence": ChangeTemplate(
        target_type="intelligence_policy",
        target_key="market.source_clustering",
        feature_flag="market.source_clustering.v1",
        payload={
            "source_clustering": True,
            "novelty_threshold": 0.72,
            "human_approval_before_core_update": True,
        },
        rollback={"source_clustering": False, "novelty_threshold": None},
    ),
}


def stage_change_for_report(report: dict, *, created_by: str, notes: str = "") -> dict:
    template = CHANGE_TEMPLATES.get(report["lab_id"])
    if not template:
        raise ValueError(f"No change template for lab_id: {report['lab_id']}")

    with db() as conn:
        existing = conn.execute(
            "SELECT * FROM staged_core_changes WHERE report_id = ?",
            (report["id"],),
        ).fetchone()
        if existing:
            return row_to_change(existing)

        change_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO staged_core_changes (
                id, report_id, lab_id, target_type, target_key, feature_flag,
                payload_json, rollback_json, status, created_at, created_by, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_id,
                report["id"],
                report["lab_id"],
                template.target_type,
                template.target_key,
                template.feature_flag,
                dumps(_build_payload(report, template)),
                dumps(template.rollback),
                "staged",
                utc_now(),
                created_by,
                notes,
            ),
        )
        row = conn.execute(
            "SELECT * FROM staged_core_changes WHERE id = ?",
            (change_id,),
        ).fetchone()
    return row_to_change(row)


def list_changes(status: str | None = None) -> list[dict]:
    query = "SELECT * FROM staged_core_changes"
    params: tuple = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_change(row) for row in rows]


def get_change(change_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM staged_core_changes WHERE id = ?",
            (change_id,),
        ).fetchone()
    return row_to_change(row) if row else None


def apply_change(change_id: str, *, applied_by: str) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM staged_core_changes WHERE id = ?",
            (change_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"Unknown change_id: {change_id}")
        if row["status"] == "applied":
            return row_to_change(row)
        if row["status"] != "staged":
            raise ValueError("Only staged changes can be applied")

        conn.execute(
            """
            UPDATE staged_core_changes
            SET status = 'applied', applied_at = ?, applied_by = ?
            WHERE id = ?
            """,
            (utc_now(), applied_by, change_id),
        )
        updated = conn.execute(
            "SELECT * FROM staged_core_changes WHERE id = ?",
            (change_id,),
        ).fetchone()
    return row_to_change(updated)


def feature_flags() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT feature_flag, target_type, target_key, status, applied_at
            FROM staged_core_changes
            ORDER BY created_at DESC
            """
        ).fetchall()
    grouped: dict[str, dict] = {}
    for row in rows:
        flag = row["feature_flag"]
        current = grouped.get(flag)
        if not current:
            current = {
                "feature_flag": row["feature_flag"],
                "target_type": row["target_type"],
                "target_key": row["target_key"],
                "enabled": False,
                "status": "staged",
                "applied_at": None,
                "staged_count": 0,
                "applied_count": 0,
            }
            grouped[flag] = current
        if row["status"] == "applied":
            current["enabled"] = True
            current["status"] = "applied"
            current["applied_count"] += 1
            current["applied_at"] = current["applied_at"] or row["applied_at"]
        elif row["status"] == "staged":
            current["staged_count"] += 1
    return list(grouped.values())


def _build_payload(report: dict, template: ChangeTemplate) -> dict:
    return {
        "feature_flag": template.feature_flag,
        "target_type": template.target_type,
        "target_key": template.target_key,
        "config": template.payload,
        "source_report": {
            "id": report["id"],
            "lab_id": report["lab_id"],
            "title": report["title"],
            "summary": report["summary"],
            "recommendation": report["recommendation"],
            "risk_level": report["risk_level"],
            "evidence": report["evidence"],
        },
    }


def row_to_change(row) -> dict:
    return {
        "id": row["id"],
        "report_id": row["report_id"],
        "lab_id": row["lab_id"],
        "target_type": row["target_type"],
        "target_key": row["target_key"],
        "feature_flag": row["feature_flag"],
        "payload": loads(row["payload_json"], {}),
        "rollback": loads(row["rollback_json"], {}),
        "status": row["status"],
        "created_at": row["created_at"],
        "created_by": row["created_by"],
        "applied_at": row["applied_at"],
        "applied_by": row["applied_by"],
        "notes": row["notes"],
    }
