"""Carga de prompts y ejecución de sub-agentes.

Cada sub-agente recibe: su system prompt (parametrizado), el contexto recuperado
por RAG (con ids de documento para citar) y la petición del usuario. Devuelve un
`AgentResult` con contenido y citas.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

from app.core.model_router import Tier, get_router
from app.core.schemas import AgentResult, Citation, RetrievedChunk

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Tier de modelo por agente (decisión coste/calidad — ver doc de arquitectura).
AGENT_TIER: dict[str, Tier] = {
    "estratega": "premium",     # razonamiento de alto valor
    "grc": "premium",           # responsabilidad regulatoria
    "investigador": "cheap",    # síntesis de resultados de búsqueda
    "constructor": "medium",
}


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, *, client_name: str, data_region: str) -> str:
    today = dt.date.today().isoformat()
    return (
        load_prompt(name)
        .replace("{{current_date}}", today)
        .replace("{{client_name}}", client_name)
        .replace("{{data_region}}", data_region)
    )


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(No hay documentos del cliente recuperados para esta consulta.)"
    lines = []
    for c in chunks:
        lines.append(f"[doc:{c.document_id}#{c.chunk_id}] {c.text}")
    return "\n\n".join(lines)


def _citations_from(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            source_id=f"{c.document_id}#{c.chunk_id}",
            source_type="document",
            snippet=c.text[:200],
            date=c.metadata.get("date"),
        )
        for c in chunks
    ]


async def run_agent(
    agent: str,
    user_message: str,
    chunks: list[RetrievedChunk],
    *,
    client_name: str,
    data_region: str,
    extra_context: str = "",
) -> AgentResult:
    system = render_prompt(agent, client_name=client_name, data_region=data_region)
    context = _format_context(chunks)
    user = (
        f"## Contexto del cliente (RAG)\n{context}\n\n"
        f"{extra_context}\n\n"
        f"## Petición\n{user_message}"
    )
    content = await get_router().complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tier=AGENT_TIER.get(agent, "medium"),
    )
    return AgentResult(
        agent=agent, content=content, citations=_citations_from(chunks)
    )
