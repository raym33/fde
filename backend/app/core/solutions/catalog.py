"""Catálogo de soluciones: curado + contribuciones humanas.

- Base curada en `app/data/solutions_catalog.json` (control de versiones).
- Contribuciones humanas en `solutions_contributions.jsonl` (append-only): el
  equipo (o expertos del cliente) añade novedades, nuevas opciones o ajustes que
  alimentan la data sin tocar el código. Las contribuciones pueden ser globales
  (`tenant_id = "*"`) o específicas de un cliente.

`match_use_case` clasifica la pregunta en una categoría por solape de keywords;
si no hay match claro, devuelve "generico" y el motor recurre al LLM/web para
proponer opciones desde cero.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from app.core.solutions.schema import SolutionOption

_BASE = Path(__file__).resolve().parents[2] / "data" / "solutions_catalog.json"
_CONTRIB = (
    Path(__file__).resolve().parents[2] / "data" / "solutions_contributions.jsonl"
)


def _load_base() -> dict:
    return json.loads(_BASE.read_text(encoding="utf-8"))


def match_use_case(query: str) -> tuple[str, str]:
    """Devuelve (use_case_id, label) por solape de keywords."""
    q = query.lower()
    best, best_hits, best_label = "generico", 0, "Caso de uso general"
    for uc in _load_base()["use_cases"]:
        hits = sum(1 for kw in uc["keywords"] if kw in q)
        if hits > best_hits:
            best, best_hits, best_label = uc["id"], hits, uc["label"]
    return best, best_label


def _load_contributions(use_case_id: str, tenant_id: str) -> list[dict]:
    if not _CONTRIB.exists():
        return []
    out = []
    for line in _CONTRIB.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("use_case_id") != use_case_id:
            continue
        if rec.get("tenant_id") in ("*", tenant_id):
            out.append(rec["option"])
    return out


def get_options(use_case_id: str, tenant_id: str) -> list[SolutionOption]:
    options: list[dict] = []
    for uc in _load_base()["use_cases"]:
        if uc["id"] == use_case_id:
            options.extend(uc["options"])
            break
    options.extend(_load_contributions(use_case_id, tenant_id))
    return [SolutionOption(**o) for o in options]


def add_contribution(
    *,
    use_case_id: str,
    option: dict,
    author: str,
    tenant_id: str = "*",
    note: str = "",
) -> None:
    """Añade una contribución humana (nueva opción) al catálogo vivo."""
    _CONTRIB.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "author": author,
        "tenant_id": tenant_id,
        "use_case_id": use_case_id,
        "note": note,
        "option": option,
    }
    with _CONTRIB.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
