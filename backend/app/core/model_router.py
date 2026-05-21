"""Router de modelos híbrido.

Enruta cada subtarea al tier de modelo más barato que la resuelve bien:

    cheap   -> open-source pequeño  (clasificar, etiquetar, resúmenes breves)
    medium  -> open-source medio    (RAG estándar, borradores)
    premium -> frontera             (razonamiento de alto riesgo, síntesis GRC)

Todo pasa por LiteLLM, de modo que cambiar de modelo/proveedor es una línea de
config (ver `config.py` / `.env`). En DEMO_MODE no se llama a ningún proveedor:
se devuelven respuestas simuladas para poder probar el flujo completo.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Literal

from app.config import get_settings
from app.core import runtime_policy
from app.security import pii
from app.tools import cli_provider
from app.tools import lm_studio

Tier = Literal["cheap", "medium", "premium"]


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._tier_map = {
            "cheap": self.settings.model_router_cheap,
            "medium": self.settings.model_router_medium,
            "premium": self.settings.model_router_premium,
        }

    def model_for(self, tier: Tier) -> str:
        provider = self.provider_for(tier)
        if provider == "lmstudio":
            by_tier = {
                "cheap": self.settings.lm_studio_model_cheap,
                "medium": self.settings.lm_studio_model_medium,
                "premium": self.settings.lm_studio_model_premium,
            }
            return by_tier[tier] or self.settings.lm_studio_chat_model
        return self._tier_map[tier]

    def provider_for(self, tier: Tier) -> str:
        policy = runtime_policy.current_policy()
        if tier == "premium":
            return policy.premium_provider
        if self.settings.local_llm_enabled and self.settings.local_llm_provider == "lmstudio":
            return "lmstudio"
        return "litellm"

    # ── Completions ────────────────────────────────────────────────
    async def complete(
        self,
        messages: list[dict],
        tier: Tier = "medium",
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        max_tokens = max_tokens or self.settings.max_tokens_per_request
        provider = self.provider_for(tier)
        if provider == "lmstudio":
            return await lm_studio.chat_completion(
                messages=messages,
                model=self.model_for(tier),
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

        if self.settings.demo_mode:
            return _demo_completion(messages, tier)

        if provider in {"claude_cli", "codex_cli"}:
            safe_messages, pii_map = _redact_messages(messages)
            text = await cli_provider.complete(provider, safe_messages)
            return pii.rehydrate(text, pii_map)

        import litellm  # import perezoso: no requerido en demo

        safe_messages, pii_map = _redact_messages(messages)
        resp = await litellm.acompletion(
            model=self.model_for(tier),
            messages=safe_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        text = resp["choices"][0]["message"]["content"] or ""
        return pii.rehydrate(text, pii_map)

    async def stream(
        self,
        messages: list[dict],
        tier: Tier = "medium",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        max_tokens = max_tokens or self.settings.max_tokens_per_request
        provider = self.provider_for(tier)
        if provider == "lmstudio":
            async for token in lm_studio.stream_chat_completion(
                messages=messages,
                model=self.model_for(tier),
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                await asyncio.sleep(0)
                yield token
            return

        if self.settings.demo_mode:
            for token in _demo_completion(messages, tier).split(" "):
                await asyncio.sleep(0.01)
                yield token + " "
            return

        if provider in {"claude_cli", "codex_cli"}:
            text = await self.complete(
                messages=messages,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            for token in text.split(" "):
                await asyncio.sleep(0)
                yield token + " "
            return

        import litellm

        safe_messages, pii_map = _redact_messages(messages)
        stream = await litellm.acompletion(
            model=self.model_for(tier),
            messages=safe_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for part in stream:
            delta = part["choices"][0]["delta"].get("content")
            if delta:
                yield pii.rehydrate(delta, pii_map)

    # ── Embeddings ─────────────────────────────────────────────────
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self.settings.local_llm_enabled and self.settings.local_llm_provider == "lmstudio":
            try:
                return await lm_studio.embeddings(texts, self.settings.lm_studio_embedding_model)
            except Exception:
                if self.settings.local_embedding_fallback:
                    return [_demo_embedding(t) for t in texts]
                raise

        if self.settings.demo_mode:
            return [_demo_embedding(t) for t in texts]

        import litellm

        resp = await litellm.aembedding(
            model=self.settings.model_embeddings, input=texts
        )
        return [item["embedding"] for item in resp["data"]]


# ── Helpers de demo ────────────────────────────────────────────────
def _demo_completion(messages: list[dict], tier: Tier) -> str:
    """Respuesta simulada determinista para desarrollo sin claves."""
    user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    system = next((m["content"] for m in messages if m["role"] == "system"), "")

    # Si es el verifier (pide JSON), devuelve un veredicto válido.
    if "Return STRICT JSON" in system or "VerifierVerdict" in system:
        return json.dumps({"approved": True, "issues": [], "revised_answer": None})

    rag_excerpt = ""
    if "## Contexto del cliente (RAG)" in user and "[doc:" in user:
        after = user.split("## Contexto del cliente (RAG)", 1)[1]
        before_next = after.split("##", 1)[0]
        rag_excerpt = before_next.strip()[:500]
        if rag_excerpt and "(sin documentos del cliente)" not in rag_excerpt:
            return (
                f"[DEMO · tier={tier}] He recuperado contexto documental del "
                f"cliente y lo usaría como fuente principal.\n\n"
                f"**Contexto recuperado:** {rag_excerpt}\n\n"
                f"**Siguiente análisis recomendado:** revisar responsables "
                f"humanos, registro de riesgos, evaluación RGPD/EU AI Act, "
                f"trazabilidad y supervisión humana. Esto no es asesoramiento "
                f"legal — consulte con un profesional cualificado."
            )

    return (
        f"[DEMO · tier={tier}] Respuesta simulada. Configura una API key y pon "
        f"DEMO_MODE=false para usar modelos reales. Petición recibida: "
        f"\"{user[:160]}\". Esto no es asesoramiento legal — consulte con un "
        f"profesional cualificado."
    )


def _demo_embedding(text: str, dim: int = 1024) -> list[float]:
    """Embedding pseudo-determinista basado en hash (solo para demo/tests)."""
    import hashlib

    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Repite el hash hasta llenar la dimensión y normaliza a [-1, 1].
    raw = (h * (dim // len(h) + 1))[:dim]
    return [(b - 128) / 128.0 for b in raw]


def _redact_messages(messages: list[dict]) -> tuple[list[dict], dict[str, str]]:
    pii_map: dict[str, str] = {}
    safe_messages = []
    for message in messages:
        content = message.get("content", "")
        safe_content, mapping = pii.redact(content)
        pii_map.update(mapping)
        safe_messages.append({**message, "content": safe_content})
    return safe_messages, pii_map


_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
