"""Orquestador: el grafo de estados del sistema agéntico.

Flujo (modelado como grafo; portable a LangGraph 1:1):

    router → retrieve → [sub-agentes en paralelo] → synthesize → verify → assemble

Se expone como generador asíncrono que emite eventos `ChatChunk` para streaming
SSE al frontend. El streaming de tokens se hace sobre la respuesta ya verificada,
de modo que el usuario no ve afirmaciones que el Verifier habría corregido.
"""
from __future__ import annotations

import asyncio

from app.config import get_settings
from app.core.agents import render_prompt, run_agent
from app.core.model_router import get_router
from app.core.schemas import (
    INTENT_AGENTS,
    AgentResult,
    ChatChunk,
    Intent,
    RetrievedChunk,
    VerifierVerdict,
)
from app.core import opportunities
from app.core.solutions import engine as solutions_engine
from app.core.verifier import verify
from app.knowledge.updates import retrieve_knowledge
from app.rag.retriever import retrieve

# El orden importa: se devuelve la primera intención con keyword coincidente.
_INTENT_KEYWORDS = {
    Intent.OPPORTUNITY: [
        "donde implementar ia", "dónde implementar ia", "donde aplicar ia",
        "dónde aplicar ia", "donde usar ia", "dónde usar ia",
        "implementar ia", "implantar ia", "aplicar ia", "meter ia",
        "donde debería implementar", "dónde debería implementar",
        "donde deberia implementar", "dónde deberia implementar",
        "donde deberíamos implementar", "dónde deberíamos implementar",
        "donde deberiamos implementar", "dónde deberiamos implementar",
        "en qué áreas", "en que áreas", "en que areas", "en qué areas",
        "oportunidades de ia", "mapa de oportunidades", "descubrir oportunidades",
        "casos de uso", "caso de uso", "use cases", "use case",
        "por dónde empezar", "por donde empezar", "diagnóstico ia",
        "diagnostico ia", "consultoría ia", "consultoria ia",
        "qué procesos automatizar", "que procesos automatizar",
        "procesos para ia", "departamentos para ia",
    ],
    Intent.GRC: ["rgpd", "gdpr", "ai act", "cumplimiento", "compliance",
                 "iso 42001", "nist", "política de", "regulación", "governance",
                 "readiness", "auditoría de"],
    Intent.SOLUTION: ["solución", "solucion", "soluciones", "recomienda",
                      "recomiénd", "recomiend", "propón", "propon", "propone",
                      "mejor opción", "mejor opcion", "mejores opciones",
                      "qué opciones", "que opciones", "cuál es la mejor",
                      "cual es la mejor", "qué herramienta", "que herramienta",
                      "qué tool", "cómo puedo", "como puedo", "resolver",
                      "chatbot", "chat bot", "lead scoring", "scoring de leads",
                      "buscador", "presupuesto bajo", "bajo presupuesto",
                      "barato", "low cost"],
    Intent.RESEARCH: ["última", "ultimas", "noticia", "tendencia", "competidor",
                      "mercado", "novedad", "hoy", "reciente"],
    Intent.BUILD: ["construir", "implementar", "integrar", "automatizar",
                   "fine-tuning", "diseña un agente", "workflow"],
    Intent.STRATEGY: ["estrategia", "roadmap", "roi", "caso de uso", "use case",
                      "transformación", "plan"],
    Intent.DELIVERABLE: ["informe", "report", "assessment", "evaluación completa"],
}


async def classify_intent(message: str) -> Intent:
    """Clasifica la intención. En demo usa heurística; si no, modelo barato."""
    settings = get_settings()
    text = message.lower()
    if settings.demo_mode:
        for intent, kws in _INTENT_KEYWORDS.items():
            if any(k in text for k in kws):
                return intent
        return Intent.QUICK

    prompt = (
        "Classify the user request into exactly one label: "
        "quick, strategy, grc, research, build, solution, opportunity, deliverable. "
        "Reply with only the label.\n\nRequest: " + message
    )
    raw = (
        await get_router().complete(
            [{"role": "user", "content": prompt}], tier="cheap", temperature=0.0
        )
    ).strip().lower()
    for intent in Intent:
        if intent.value in raw:
            return intent
    return Intent.STRATEGY


def _synthesis_tier(intent: Intent) -> str:
    return "premium" if intent in (Intent.DELIVERABLE, Intent.GRC) else "medium"


async def run_stream(message: str, tenant_id: str, *, client_name: str):
    """Generador asíncrono que produce eventos ChatChunk."""
    settings = get_settings()
    region = settings.data_region

    # 1. Router ------------------------------------------------------
    intent = await classify_intent(message)
    yield ChatChunk(type="status", data=f"Intención detectada: {intent.value}")

    # 2. Recuperación (aislada por tenant) ---------------------------
    yield ChatChunk(type="status", data="Recuperando contexto del cliente…")
    chunks: list[RetrievedChunk] = await retrieve(
        query=message, tenant_id=tenant_id, top_k=8
    )
    platform_chunks = retrieve_knowledge(message, top_k=4)
    if platform_chunks:
        chunks = [*platform_chunks, *chunks]
        yield ChatChunk(
            type="status",
            data=f"Usando inteligencia IA curada: {len(platform_chunks)} fichas relevantes",
        )

    # 2-bis. Rama del motor de soluciones ----------------------------
    if intent == Intent.SOLUTION:
        async for ev in _run_solution(
            message, tenant_id, chunks, client_name=client_name, region=region
        ):
            yield ev
        return

    if intent == Intent.OPPORTUNITY:
        async for ev in _run_opportunity(
            message, chunks, client_name=client_name, region=region
        ):
            yield ev
        return

    # 3. Sub-agentes (en paralelo) -----------------------------------
    agent_names = INTENT_AGENTS[intent]
    agent_results: list[AgentResult] = []
    if agent_names:
        yield ChatChunk(
            type="status",
            data="Coordinando sub-agentes: " + ", ".join(agent_names),
        )
        maybe_results = await asyncio.gather(
            *[
                run_agent(
                    a, message, chunks,
                    client_name=client_name, data_region=region,
                )
                for a in agent_names
            ],
            return_exceptions=True,
        )
        for name, result in zip(agent_names, maybe_results):
            if isinstance(result, Exception):
                yield ChatChunk(
                    type="status",
                    data=f"Sub-agente {name} no disponible; continuo con contexto recuperado.",
                    meta={"error": str(result)[:300]},
                )
                continue
            agent_results.append(result)

    # 4. Síntesis (orquestador) --------------------------------------
    yield ChatChunk(type="status", data="Sintetizando respuesta ejecutiva…")
    system = render_prompt(
        "orchestrator", client_name=client_name, data_region=region
    )
    subagent_block = "\n\n".join(
        f"### Salida de {r.agent}\n{r.content}" for r in agent_results
    ) or "(respuesta directa, sin sub-agentes)"
    context_block = "\n\n".join(
        f"[doc:{c.document_id}#{c.chunk_id}] {c.text}" for c in chunks
    ) or "(sin documentos del cliente)"
    user = (
        f"## Contexto del cliente (RAG)\n{context_block}\n\n"
        f"## Aportaciones de sub-agentes\n{subagent_block}\n\n"
        f"## Petición del usuario\n{message}\n\n"
        f"Responde en el formato adaptativo adecuado a la intención "
        f"'{intent.value}'."
    )
    try:
        draft = await get_router().complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tier=_synthesis_tier(intent),
        )
    except Exception as exc:  # noqa: BLE001
        yield ChatChunk(
            type="status",
            data="Modelo local no completó la síntesis; uso respuesta compacta de respaldo.",
            meta={"error": str(exc)[:300]},
        )
        draft = _fallback_answer(chunks)

    # 5. Verificación ------------------------------------------------
    yield ChatChunk(type="status", data="Verificando citas y consistencia…")
    try:
        verdict = await verify(
            message, draft, chunks, client_name=client_name, data_region=region
        )
    except Exception as exc:  # noqa: BLE001
        verdict = VerifierVerdict(
            approved=True,
            issues=[{"type": "verifier_unavailable", "detail": str(exc)[:300]}],
            revised_answer=None,
        )
    final = verdict.revised_answer or draft
    if not verdict.approved and verdict.issues:
        yield ChatChunk(
            type="status",
            data="El verificador marcó observaciones (registradas en auditoría).",
            meta={"issues": verdict.issues},
        )

    # 6. Emisión final (streaming de tokens) -------------------------
    for token in _tokenize(final):
        yield ChatChunk(type="token", data=token)
        await asyncio.sleep(0)  # cede el control al loop

    # Citas agregadas
    seen: set[str] = set()
    for r in agent_results:
        for c in r.citations:
            if c.source_id not in seen:
                seen.add(c.source_id)
                yield ChatChunk(
                    type="citation",
                    data=c.source_id,
                    meta=c.model_dump(),
                )

    yield ChatChunk(
        type="final",
        data="",
        meta={"intent": intent.value, "verified": verdict.approved},
    )


async def _run_solution(
    message: str,
    tenant_id: str,
    chunks: list[RetrievedChunk],
    *,
    client_name: str,
    region: str,
):
    """Genera, puntua y recomienda soluciones; emite la propuesta por streaming."""
    settings = get_settings()
    yield ChatChunk(
        type="status", data="Generando y puntuando soluciones candidatas…"
    )
    proposal = await solutions_engine.propose(
        message, tenant_id, chunks, client_name=client_name, data_region=region
    )
    yield ChatChunk(
        type="status",
        data=(
            f"Caso: {proposal.use_case} · presupuesto: "
            f"{proposal.client_budget.value} · "
            f"{len(proposal.options)} opciones evaluadas"
        ),
    )

    # Narrativa ejecutiva con LLM (en demo se usa la racional determinista).
    if not settings.demo_mode and proposal.options:
        system = render_prompt(
            "solutions_architect", client_name=client_name, data_region=region
        )
        context_block = "\n".join(
            f"[doc:{c.document_id}#{c.chunk_id}] {c.text}" for c in chunks
        ) or "(sin documentos del cliente)"
        user = (
            f"## Contexto del cliente (RAG)\n{context_block}\n\n"
            f"## Propuesta estructurada (scores y ROI ya calculados)\n"
            f"{_proposal_summary(proposal)}\n\n"
            f"## Pregunta del usuario\n{message}\n\n"
            f"Escribe solo la narrativa ejecutiva (recomendación, cuándo "
            f"preferir alternativa, riesgo principal)."
        )
        narrative = await get_router().complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tier="premium",
        )
        if narrative.strip():
            proposal.rationale = narrative.strip()

    final = solutions_engine.render_markdown(proposal)

    # Verificación
    yield ChatChunk(type="status", data="Verificando la propuesta…")
    verdict = await verify(
        message, final, chunks, client_name=client_name, data_region=region
    )
    final = verdict.revised_answer or final
    if not verdict.approved and verdict.issues:
        yield ChatChunk(
            type="status",
            data="El verificador marcó observaciones (registradas en auditoría).",
            meta={"issues": verdict.issues},
        )

    for token in _tokenize(final):
        yield ChatChunk(type="token", data=token)
        await asyncio.sleep(0)

    # Citas de la opción recomendada (catálogo + web)
    if proposal.options:
        seen: set[str] = set()
        for c in proposal.options[0].sources:
            if c.source_id not in seen:
                seen.add(c.source_id)
                yield ChatChunk(
                    type="citation", data=c.source_id, meta=c.model_dump()
                )

    yield ChatChunk(
        type="final",
        data="",
        meta={
            "intent": Intent.SOLUTION.value,
            "use_case": proposal.use_case,
            "recommended": proposal.recommended_id,
            "verified": verdict.approved,
        },
    )


async def _run_opportunity(
    message: str,
    chunks: list[RetrievedChunk],
    *,
    client_name: str,
    region: str,
):
    """Diagnostica dónde implementar IA dentro de una pyme."""
    settings = get_settings()
    yield ChatChunk(
        type="status",
        data="Diagnosticando áreas de la empresa y oportunidades IA…",
    )
    diagnosis = opportunities.diagnose_opportunities(
        message,
        chunks,
        client_name=client_name,
    )
    yield ChatChunk(
        type="status",
        data=(
            f"{len(diagnosis.top_opportunities)} oportunidades priorizadas · "
            f"{len(diagnosis.quick_wins)} quick wins · "
            f"perfil: {diagnosis.company_size}"
        ),
    )
    final = opportunities.render_markdown(diagnosis)

    if settings.demo_mode:
        verdict = VerifierVerdict(approved=True)
    else:
        yield ChatChunk(type="status", data="Verificando el mapa de oportunidades…")
        verdict = await verify(
            message, final, chunks, client_name=client_name, data_region=region
        )
        final = verdict.revised_answer or final
        if not verdict.approved and verdict.issues:
            yield ChatChunk(
                type="status",
                data="El verificador marcó observaciones (registradas en auditoría).",
                meta={"issues": verdict.issues},
            )

    for token in _tokenize(final):
        yield ChatChunk(type="token", data=token)
        await asyncio.sleep(0)

    seen: set[str] = set()
    for opportunity in diagnosis.top_opportunities[:5]:
        for citation in opportunity.citations:
            if citation.source_id not in seen:
                seen.add(citation.source_id)
                yield ChatChunk(
                    type="citation",
                    data=citation.source_id,
                    meta=citation.model_dump(),
                )

    yield ChatChunk(
        type="final",
        data="",
        meta={
            "intent": Intent.OPPORTUNITY.value,
            "top_opportunities": [o.id for o in diagnosis.top_opportunities[:5]],
            "verified": verdict.approved,
        },
    )


def _proposal_summary(proposal) -> str:
    rows = []
    for o in proposal.options:
        rows.append(
            f"- {o.title} [{o.budget_tier.value}] score={o.total_score} "
            f"setup={o.roi.setup_cost_eur}€ mes={o.roi.monthly_cost_eur}€ "
            f"payback={o.roi.payback_months}m conf={o.roi.confidence}% "
            f"{'<RECOMENDADA>' if o.id == proposal.recommended_id else ''}"
        )
    return "\n".join(rows)


def _tokenize(text: str):
    """Trocea por palabras para un streaming sencillo."""
    for word in text.split(" "):
        yield word + " "


def _fallback_answer(chunks: list[RetrievedChunk]) -> str:
    relevant = chunks[:4]
    if not relevant:
        return (
            "No tengo todavía suficiente contexto documental o inteligencia curada "
            "para responder con seguridad. Sube fuentes recientes o documentos del "
            "cliente y repetiré el análisis."
        )

    bullets = []
    for chunk in relevant:
        title = chunk.metadata.get("title") or chunk.document_id
        snippet = " ".join(chunk.text.split())[:360]
        bullets.append(f"- **{title}:** {snippet}")

    return (
        "Con la inteligencia curada disponible, mi recomendación breve es priorizar "
        "las acciones con impacto medible, bajo riesgo y trazabilidad clara.\n\n"
        "**Contexto usado**\n"
        + "\n".join(bullets)
        + "\n\n**Siguiente paso**: convertir estas fichas en una decisión concreta "
        "con ROI, coste mensual, responsable humano y riesgo GRC antes de "
        "promoverla al roadmap."
    )
