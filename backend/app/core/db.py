import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    db_path = get_settings().sqlite_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterable[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lab_experiments (
                id TEXT PRIMARY KEY,
                lab_id TEXT NOT NULL,
                triggered_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parameters_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lab_runs (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                lab_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                baseline_score REAL NOT NULL,
                new_score REAL NOT NULL,
                improvement_pct REAL NOT NULL,
                threshold_pct REAL NOT NULL,
                metrics_json TEXT NOT NULL,
                notes TEXT NOT NULL,
                FOREIGN KEY(experiment_id) REFERENCES lab_experiments(id)
            );

            CREATE TABLE IF NOT EXISTS core_reports (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                lab_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                rollout_plan TEXT NOT NULL,
                rollback_plan TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by TEXT,
                decision_notes TEXT,
                FOREIGN KEY(run_id) REFERENCES lab_runs(id)
            );

            CREATE TABLE IF NOT EXISTS staged_core_changes (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL UNIQUE,
                lab_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_key TEXT NOT NULL,
                feature_flag TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                rollback_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                applied_at TEXT,
                applied_by TEXT,
                notes TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES core_reports(id)
            );

            CREATE TABLE IF NOT EXISTS knowledge_updates (
                id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                source_url TEXT,
                source_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                parser TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_briefs (
                id TEXT PRIMARY KEY,
                update_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                business_relevance TEXT NOT NULL,
                technical_relevance TEXT NOT NULL,
                risk_relevance TEXT NOT NULL,
                compact_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(update_id) REFERENCES knowledge_updates(id)
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_updates_uploaded_at
                ON knowledge_updates(uploaded_at);

            CREATE INDEX IF NOT EXISTS idx_knowledge_briefs_update_id
                ON knowledge_briefs(update_id);

            CREATE TABLE IF NOT EXISTS tenant_runtime_policies (
                tenant_id TEXT PRIMARY KEY,
                premium_provider TEXT NOT NULL,
                escalation_enabled INTEGER NOT NULL,
                escalation_allow_sensitive INTEGER NOT NULL,
                escalation_allowed_intents TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            );
            """
        )


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)
