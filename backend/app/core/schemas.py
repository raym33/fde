"""Modelos pydantic compartidos por el núcleo agéntico."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """Intención detectada por el router del orquestador."""

    QUICK = "quick"            # pregunta simple / follow-up
    STRATEGY = "strategy"      # estrategia, roadmap, ROI
    GRC = "grc"                # gobernanza, riesgo, cumplimiento
    RESEARCH = "research"      # requiere datos externos al día
    BUILD = "build"            # diseñar un agente/workflow
    SOLUTION = "solution"      # proponer la mejor solución a una pregunta
    DELIVERABLE = "deliverable"  # entregable ejecutivo completo


# Qué sub-agentes activa cada intención.
INTENT_AGENTS: dict[Intent, list[str]] = {
    Intent.QUICK: [],
    Intent.STRATEGY: ["estratega"],
    Intent.GRC: ["grc"],
    Intent.RESEARCH: ["investigador"],
    Intent.BUILD: ["constructor"],
    Intent.SOLUTION: [],        # gestionado por el motor de soluciones
    Intent.DELIVERABLE: ["investigador", "estratega", "grc"],
}


class Citation(BaseModel):
    source_id: str                 # document id o URL
    source_type: Literal["document", "web", "knowledge_base"]
    snippet: str
    date: str | None = None        # fecha de la fuente (ISO) si aplica


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent: str
    content: str
    citations: list[Citation] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatChunk(BaseModel):
    """Evento que se envía al frontend por SSE."""

    type: Literal["status", "token", "citation", "final", "error"]
    data: str
    meta: dict = Field(default_factory=dict)


class VerifierVerdict(BaseModel):
    approved: bool
    issues: list[dict] = Field(default_factory=list)
    revised_answer: str | None = None
