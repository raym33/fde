from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import get_settings
from app.core.db import init_db
from app.knowledge import updates


ROOT = Path(__file__).resolve().parents[1]


def _init_temp_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LABS_SQLITE_PATH", str(tmp_path / "knowledge.sqlite3"))
    get_settings.cache_clear()
    init_db()


async def _ingest_markdown(path: Path, source_type: str) -> None:
    await updates.ingest_update(
        raw=path.read_bytes(),
        filename=path.name,
        content_type="text/markdown",
        title=path.read_text(encoding="utf-8").splitlines()[0].replace("# ", "").strip(),
        source_url=None,
        source_type=source_type,
        scope="global",
        uploaded_by="pytest",
    )


def _seed_foundations() -> None:
    files = [
        ROOT / "backend/app/data/curated_intel/fundamentos/01-fundamentos-diagnostico-pyme.md",
        ROOT / "backend/app/data/curated_intel/fundamentos/02-playbook-local-vs-cloud.md",
        ROOT / "backend/app/data/curated_intel/fundamentos/03-biblioteca-quick-wins-sectoriales.md",
        ROOT / "backend/app/data/curated_intel/fundamentos/04-gobierno-minimo-viable.md",
        ROOT / "backend/app/data/curated_intel/fundamentos/05-roi-y-priorizacion.md",
        ROOT / "backend/app/data/curated_intel/fundamentos/06-mapeo-de-procesos-y-descubrimiento.md",
        ROOT / "backend/app/data/curated_intel/2026-05-21/05-dolores-local-cloud-gobierno.md",
    ]
    for path in files:
        source_type = "curated_foundation" if "fundamentos" in str(path) else "curated_operator_intel"
        asyncio.run(_ingest_markdown(path, source_type))


def test_broad_query_prefers_foundations(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("donde implementar IA primero en una pyme", top_k=3)

    assert hits
    assert hits[0].metadata["title"] == "FUNDAMENTOS DE DIAGNOSTICO PYME — BASE"


def test_local_vs_cloud_prefers_playbook(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("local vs cloud datos sensibles", top_k=3)

    assert hits
    assert hits[0].metadata["title"] == "PLAYBOOK LOCAL VS CLOUD — BASE"


def test_roi_query_prefers_roi_playbook(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("como calcular ROI de automatizar correos", top_k=3)

    assert hits
    assert hits[0].metadata["title"] == "ROI Y PRIORIZACION DE IA — BASE"


def test_sector_query_prefers_sector_library(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("quick wins para clinica", top_k=3)

    assert hits
    assert hits[0].metadata["title"] == "BIBLIOTECA DE QUICK WINS SECTORIALES — BASE"


def test_query_intent_metadata_is_exposed(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("local vs cloud datos sensibles", top_k=2)

    assert hits
    assert hits[0].metadata["query_intent"] == "local_cloud"
    assert hits[0].metadata["block"] in {"fundamentos", "dolores", "stack"}


def test_governance_style_query_prefers_governance_content(monkeypatch, tmp_path) -> None:
    _init_temp_db(monkeypatch, tmp_path)
    _seed_foundations()

    hits = updates.retrieve_knowledge("ChatGPT en PC de clinica sin control", top_k=3)

    assert hits
    titles = [hit.metadata["title"] for hit in hits]
    assert "GOBIERNO MINIMO VIABLE DE IA — BASE" in titles
