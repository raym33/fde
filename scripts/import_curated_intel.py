#!/usr/bin/env python3
"""Import curated operator intelligence into the local knowledge base.

This keeps a versioned source of truth in git while loading compact briefs into
the local SQLite knowledge store used by VirtuDirector IA.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATED_DIR = ROOT / "backend" / "app" / "data" / "curated_intel"
BACKEND_DIR = ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import init_db
from app.knowledge import updates


def _title_from_markdown(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").strip()


async def import_one(path: Path, *, uploaded_by: str, scope: str, source_type: str) -> tuple[str, str, int]:
    raw = path.read_bytes()
    result = await updates.ingest_update(
        raw=raw,
        filename=path.name,
        content_type="text/markdown",
        title=_title_from_markdown(path),
        source_url=None,
        source_type=source_type,
        scope=scope,
        uploaded_by=uploaded_by,
    )
    status = "duplicate" if result.duplicate else "accepted"
    return path.name, status, result.rag_chunks


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="Subcarpeta de fecha dentro de curated_intel")
    parser.add_argument("--uploaded-by", default="seed-import")
    parser.add_argument("--scope", default="global", choices=["global", "internal"])
    parser.add_argument("--source-type", default="curated_operator_intel")
    args = parser.parse_args()

    init_db()
    base = CURATED_DIR / args.date if args.date else CURATED_DIR
    if not base.exists():
        raise SystemExit(f"No existe la carpeta: {base}")

    files = sorted(base.rglob("*.md"))
    if not files:
        raise SystemExit(f"No hay markdowns para importar en: {base}")

    print(f"Importando {len(files)} documentos desde {base}")
    imported = 0
    duplicates = 0
    for path in files:
        name, status, rag_chunks = await import_one(
            path,
            uploaded_by=args.uploaded_by,
            scope=args.scope,
            source_type=args.source_type,
        )
        if status == "duplicate":
            duplicates += 1
        else:
            imported += 1
        print(f"- {name}: {status} (rag_chunks={rag_chunks})")

    current = updates.status()
    print(
        f"Estado final: updates={current['updates']} briefs={current['briefs']} "
        f"imported={imported} duplicates={duplicates}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
