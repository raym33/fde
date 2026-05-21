from dataclasses import asdict
import traceback
from typing import Optional
from uuid import uuid4

from app.core.db import db, dumps, loads, utc_now
from app.labs import change_registry
from app.labs.catalog import LAB_DEFINITIONS, LABS_BY_ID
from app.labs.registry import LAB_CLASSES, make_lab


class LabsService:
    def list_catalog(self) -> list[dict]:
        return [asdict(lab) for lab in LAB_DEFINITIONS]

    def schedule_preview(self) -> list[dict]:
        return [
            {
                "lab_id": lab.id,
                "cadence": lab.cadence,
                "threshold_pct": lab.threshold_pct,
                "human_approval_required": True,
            }
            for lab in LAB_DEFINITIONS
        ]

    def run_experiment(self, lab_id: Optional[str] = None, triggered_by: str = "api") -> dict:
        lab_ids = [lab_id] if lab_id else list(LAB_CLASSES.keys())
        runs = []
        reports = []
        for current_lab_id in lab_ids:
            if current_lab_id not in LABS_BY_ID:
                raise KeyError(f"Unknown lab_id: {current_lab_id}")
            run, report = self._run_one(current_lab_id, triggered_by)
            runs.append(run)
            if report:
                reports.append(report)
        return {"runs": runs, "reports": reports}

    def list_reports(self, status: Optional[str] = None) -> list[dict]:
        query = "SELECT * FROM core_reports"
        params: tuple = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        with db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_report(row) for row in rows]

    def list_runs(self, limit: int = 20) -> list[dict]:
        with db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM lab_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_report(self, report_id: str) -> Optional[dict]:
        with db() as conn:
            row = conn.execute("SELECT * FROM core_reports WHERE id = ?", (report_id,)).fetchone()
        return self._row_to_report(row) if row else None

    def decide_report(self, report_id: str, decision: str, decided_by: str, notes: str = "") -> dict:
        decision = decision.lower().strip()
        allowed = {"approve": "approved", "reject": "rejected", "implement": "implemented"}
        if decision not in allowed:
            raise ValueError("decision must be one of: approve, reject, implement")

        with db() as conn:
            row = conn.execute("SELECT * FROM core_reports WHERE id = ?", (report_id,)).fetchone()
            if not row:
                raise KeyError(f"Unknown report_id: {report_id}")
            current_status = row["status"]
            next_status = allowed[decision]
            if next_status == "implemented" and current_status != "approved":
                raise ValueError("Only approved reports can be marked as implemented")
            if current_status == "implemented":
                raise ValueError("Implemented reports are immutable")

            change = None
            if next_status == "approved":
                report_payload = self._row_to_report(row)
                change = change_registry.stage_change_for_report(
                    report_payload,
                    created_by=decided_by,
                    notes="Staged automatically after report approval.",
                )
            elif next_status == "implemented":
                report_payload = self._row_to_report(row)
                staged = change_registry.stage_change_for_report(
                    report_payload,
                    created_by=decided_by,
                    notes="Staged automatically during implementation.",
                )
                change = change_registry.apply_change(staged["id"], applied_by=decided_by)

            conn.execute(
                """
                UPDATE core_reports
                SET status = ?, decided_at = ?, decided_by = ?, decision_notes = ?
                WHERE id = ?
                """,
                (next_status, utc_now(), decided_by, notes, report_id),
            )
            updated = conn.execute("SELECT * FROM core_reports WHERE id = ?", (report_id,)).fetchone()
        response = self._row_to_report(updated)
        if change:
            response["change"] = change
        return response

    def list_changes(self, status: Optional[str] = None) -> list[dict]:
        return change_registry.list_changes(status=status)

    def get_change(self, change_id: str) -> Optional[dict]:
        return change_registry.get_change(change_id)

    def apply_change(self, change_id: str, applied_by: str) -> dict:
        change = change_registry.apply_change(change_id, applied_by=applied_by)
        with db() as conn:
            conn.execute(
                """
                UPDATE core_reports
                SET status = 'implemented', decided_at = ?, decided_by = ?,
                    decision_notes = ?
                WHERE id = ?
                """,
                (
                    utc_now(),
                    applied_by,
                    f"Implemented via staged change {change_id}.",
                    change["report_id"],
                ),
            )
        return change

    def feature_flags(self) -> list[dict]:
        return change_registry.feature_flags()

    def _run_one(self, lab_id: str, triggered_by: str) -> tuple[dict, Optional[dict]]:
        experiment_id = str(uuid4())
        run_id = str(uuid4())
        now = utc_now()
        lab = make_lab(lab_id)
        with db() as conn:
            conn.execute(
                """
                INSERT INTO lab_experiments (id, lab_id, triggered_by, created_at, parameters_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (experiment_id, lab_id, triggered_by, now, dumps({"source": "manual_or_api"})),
            )

        try:
            result = lab.run()
            self._validate_result(lab_id, result)
        except Exception as exc:
            return self._record_failed_run(
                run_id=run_id,
                experiment_id=experiment_id,
                lab_id=lab_id,
                started_at=now,
                exc=exc,
            ), None

        status = "report_proposed" if result.produces_report else "no_material_improvement"

        with db() as conn:
            conn.execute(
                """
                INSERT INTO lab_runs (
                    id, experiment_id, lab_id, status, started_at, finished_at,
                    baseline_score, new_score, improvement_pct, threshold_pct, metrics_json, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    experiment_id,
                    lab_id,
                    status,
                    now,
                    utc_now(),
                    result.baseline_score,
                    result.new_score,
                    result.improvement_pct,
                    result.threshold_pct,
                    dumps(result.metrics),
                    result.notes,
                ),
            )

        run_payload = {
            "id": run_id,
            "experiment_id": experiment_id,
            "lab_id": lab_id,
            "status": status,
            "baseline_score": result.baseline_score,
            "new_score": result.new_score,
            "improvement_pct": round(result.improvement_pct, 2),
            "threshold_pct": result.threshold_pct,
            "metrics": result.metrics,
            "notes": result.notes,
        }

        if not result.produces_report:
            return run_payload, None

        draft = lab.build_report(result)
        self._validate_draft(lab_id, draft)
        report_id = str(uuid4())
        with db() as conn:
            conn.execute(
                """
                INSERT INTO core_reports (
                    id, run_id, lab_id, title, summary, recommendation, evidence_json,
                    metrics_json, risk_level, rollout_plan, rollback_plan, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    run_id,
                    lab_id,
                    draft.title,
                    draft.summary,
                    draft.recommendation,
                    dumps(draft.evidence),
                    dumps(draft.metrics),
                    draft.risk_level,
                    draft.rollout_plan,
                    draft.rollback_plan,
                    draft.status,
                    utc_now(),
                ),
            )
            row = conn.execute("SELECT * FROM core_reports WHERE id = ?", (report_id,)).fetchone()
        return run_payload, self._row_to_report(row)

    def _record_failed_run(
        self,
        run_id: str,
        experiment_id: str,
        lab_id: str,
        started_at: str,
        exc: Exception,
    ) -> dict:
        error_payload = {
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }
        notes = f"Lab failed: {exc.__class__.__name__}: {exc}"
        with db() as conn:
            conn.execute(
                """
                INSERT INTO lab_runs (
                    id, experiment_id, lab_id, status, started_at, finished_at,
                    baseline_score, new_score, improvement_pct, threshold_pct, metrics_json, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    experiment_id,
                    lab_id,
                    "failed",
                    started_at,
                    utc_now(),
                    0.0,
                    0.0,
                    0.0,
                    LABS_BY_ID[lab_id].threshold_pct,
                    dumps(error_payload),
                    notes,
                ),
            )
        return {
            "id": run_id,
            "experiment_id": experiment_id,
            "lab_id": lab_id,
            "status": "failed",
            "baseline_score": 0.0,
            "new_score": 0.0,
            "improvement_pct": 0.0,
            "threshold_pct": LABS_BY_ID[lab_id].threshold_pct,
            "metrics": error_payload,
            "notes": notes,
        }

    def _validate_result(self, lab_id: str, result) -> None:
        if result.lab_id != lab_id:
            raise ValueError(f"Lab returned lab_id={result.lab_id!r}, expected {lab_id!r}")
        for field in ("baseline_score", "new_score"):
            score = getattr(result, field)
            if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                raise ValueError(f"{field} must be a numeric score between 0 and 100")
        if result.threshold_pct < 0:
            raise ValueError("threshold_pct must be non-negative")
        if not isinstance(result.metrics, dict) or not result.metrics:
            raise ValueError("metrics must be a non-empty dict")
        if "baseline" not in result.metrics or "candidate" not in result.metrics:
            raise ValueError("metrics must include baseline and candidate sections")

    def _validate_draft(self, lab_id: str, draft) -> None:
        if draft.lab_id != lab_id:
            raise ValueError(f"Report draft lab_id={draft.lab_id!r}, expected {lab_id!r}")
        required_text = {
            "title": draft.title,
            "summary": draft.summary,
            "recommendation": draft.recommendation,
            "rollout_plan": draft.rollout_plan,
            "rollback_plan": draft.rollback_plan,
        }
        empty = [name for name, value in required_text.items() if not value.strip()]
        if empty:
            raise ValueError(f"Report draft has empty fields: {', '.join(empty)}")
        if draft.risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be one of: low, medium, high")
        if draft.status != "proposed":
            raise ValueError("new report drafts must start with status='proposed'")
        if not draft.evidence:
            raise ValueError("report evidence must not be empty")
        if not isinstance(draft.metrics, dict) or not draft.metrics:
            raise ValueError("report metrics must be a non-empty dict")

    def _row_to_report(self, row) -> dict:
        return {
            "id": row["id"],
            "run_id": row["run_id"],
            "lab_id": row["lab_id"],
            "title": row["title"],
            "summary": row["summary"],
            "recommendation": row["recommendation"],
            "evidence": loads(row["evidence_json"], []),
            "metrics": loads(row["metrics_json"], {}),
            "risk_level": row["risk_level"],
            "rollout_plan": row["rollout_plan"],
            "rollback_plan": row["rollback_plan"],
            "status": row["status"],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
            "decided_by": row["decided_by"],
            "decision_notes": row["decision_notes"],
        }

    def _row_to_run(self, row) -> dict:
        return {
            "id": row["id"],
            "experiment_id": row["experiment_id"],
            "lab_id": row["lab_id"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "baseline_score": row["baseline_score"],
            "new_score": row["new_score"],
            "improvement_pct": round(row["improvement_pct"], 2),
            "threshold_pct": row["threshold_pct"],
            "metrics": loads(row["metrics_json"], {}),
            "notes": row["notes"],
        }
