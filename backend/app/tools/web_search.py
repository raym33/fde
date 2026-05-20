"""Búsqueda web/news pluggable para agentes.

Proveedores soportados:
  - Brave Search API
  - Tavily Search API
  - Perplexity Search API

Reglas de producto:
  - Si no hay clave o `DEMO_MODE=true`, devuelve resultados demo etiquetados.
  - Nunca finge haber usado una herramienta real.
  - Incluye caché local de corta duración para labs y market intelligence.
  - Distingue límites de tasa/autenticación para que el core pueda degradar bien.
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel

from app.config import get_settings

Provider = Literal["demo", "brave", "tavily", "perplexity"]


class WebSearchError(RuntimeError):
    """Error genérico de búsqueda externa."""


class WebSearchAuthError(WebSearchError):
    """Clave ausente o inválida."""


class WebSearchRateLimitError(WebSearchError):
    """Proveedor respondió con límite de tasa/cuota."""


class WebResult(BaseModel):
    title: str
    url: str
    snippet: str
    published: str | None = None
    source: str = "demo"
    provider: Provider = "demo"


@dataclass
class _CacheEntry:
    expires_at: float
    results: list[WebResult]


_CACHE: dict[str, _CacheEntry] = {}


def configured_provider() -> Provider:
    settings = get_settings()
    provider = settings.search_provider.lower().strip()
    if settings.demo_mode or provider == "demo":
        return "demo"
    if provider == "auto":
        if settings.brave_search_api_key:
            return "brave"
        if settings.tavily_api_key:
            return "tavily"
        if settings.perplexity_api_key:
            return "perplexity"
        return "demo"
    if provider in {"brave", "tavily", "perplexity"}:
        return provider  # type: ignore[return-value]
    return "demo"


def is_available() -> bool:
    """True si hay un proveedor real listo para uso."""
    return configured_provider() != "demo"


def status() -> dict:
    settings = get_settings()
    provider = configured_provider()
    return {
        "provider": provider,
        "available": provider != "demo",
        "demo_mode": settings.demo_mode,
        "configured_keys": {
            "brave": bool(settings.brave_search_api_key),
            "tavily": bool(settings.tavily_api_key),
            "perplexity": bool(settings.perplexity_api_key),
        },
        "cache_entries": len(_CACHE),
        "cache_ttl_seconds": settings.web_search_cache_ttl_seconds,
    }


async def search(
    query: str,
    max_results: int = 5,
    *,
    topic: str = "general",
    freshness: str = "month",
    country: str | None = None,
    language: str | None = None,
) -> list[WebResult]:
    """Busca en el proveedor configurado y normaliza resultados.

    `freshness` usa valores semánticos: day/week/month/year.
    """
    settings = get_settings()
    provider = configured_provider()
    max_results = max(1, min(int(max_results), 20))
    country = country or settings.web_search_default_country
    language = language or settings.web_search_default_language

    cache_key = f"{provider}|{query}|{max_results}|{topic}|{freshness}|{country}|{language}"
    cached = _CACHE.get(cache_key)
    if cached and cached.expires_at > time.time():
        return cached.results

    if provider == "demo":
        results = _demo_results(query, max_results)
    elif provider == "brave":
        results = await _brave_search(query, max_results, freshness, country, language)
    elif provider == "tavily":
        results = await _tavily_search(query, max_results, topic, freshness, country)
    elif provider == "perplexity":
        results = await _perplexity_search(query, max_results, freshness, country, language)
    else:
        results = _demo_results(query, max_results)

    _CACHE[cache_key] = _CacheEntry(
        expires_at=time.time() + settings.web_search_cache_ttl_seconds,
        results=results,
    )
    return results


async def _brave_search(
    query: str,
    max_results: int,
    freshness: str,
    country: str,
    language: str,
) -> list[WebResult]:
    settings = get_settings()
    if not settings.brave_search_api_key:
        raise WebSearchAuthError("BRAVE_SEARCH_API_KEY is not configured")

    freshness_map = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}
    params = {
        "q": query,
        "count": max_results,
        "country": country.lower(),
        "search_lang": language.lower(),
        "safesearch": "moderate",
    }
    if freshness in freshness_map:
        params["freshness"] = freshness_map[freshness]

    data = await _request_json(
        "GET",
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": settings.brave_search_api_key,
        },
        params=params,
        provider="brave",
    )
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            WebResult(
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                snippet=item.get("description") or item.get("snippet") or "",
                published=item.get("published"),
                source="Brave Search",
                provider="brave",
            )
        )
    return [r for r in results if r.url][:max_results]


async def _tavily_search(
    query: str,
    max_results: int,
    topic: str,
    freshness: str,
    country: str,
) -> list[WebResult]:
    settings = get_settings()
    if not settings.tavily_api_key:
        raise WebSearchAuthError("TAVILY_API_KEY is not configured")

    body = {
        "query": query,
        "search_depth": "basic",
        "topic": topic if topic in {"general", "news", "finance"} else "general",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }
    if freshness in {"day", "week", "month", "year"}:
        body["time_range"] = freshness
    if topic == "general" and country:
        body["country"] = _tavily_country(country)

    data = await _request_json(
        "POST",
        "https://api.tavily.com/search",
        headers={
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        provider="tavily",
    )
    results = []
    for item in data.get("results", []):
        results.append(
            WebResult(
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                snippet=item.get("content") or "",
                published=None,
                source="Tavily Search",
                provider="tavily",
            )
        )
    return [r for r in results if r.url][:max_results]


async def _perplexity_search(
    query: str,
    max_results: int,
    freshness: str,
    country: str,
    language: str,
) -> list[WebResult]:
    settings = get_settings()
    if not settings.perplexity_api_key:
        raise WebSearchAuthError("PERPLEXITY_API_KEY is not configured")

    body = {
        "query": query,
        "country": country.upper()[:2],
        "max_results": max_results,
        "search_language_filter": [language.lower()[:2]],
    }
    if freshness in {"hour", "day", "week", "month", "year"}:
        body["search_recency_filter"] = freshness

    data = await _request_json(
        "POST",
        "https://api.perplexity.ai/search",
        headers={
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        provider="perplexity",
    )
    results = []
    for item in data.get("results", []):
        results.append(
            WebResult(
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                snippet=item.get("snippet") or "",
                published=item.get("date") or item.get("last_updated"),
                source="Perplexity Search",
                provider="perplexity",
            )
        )
    return [r for r in results if r.url][:max_results]


async def _request_json(method: str, url: str, *, provider: Provider, **kwargs) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.web_search_timeout_seconds) as client:
        response = await client.request(method, url, **kwargs)
    if response.status_code in {401, 403}:
        raise WebSearchAuthError(f"{provider} authentication failed")
    if response.status_code in {429, 432, 433}:
        raise WebSearchRateLimitError(f"{provider} rate limit or quota reached")
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise WebSearchError(f"{provider} search failed: HTTP {response.status_code}") from exc
    return response.json()


def _demo_results(query: str, max_results: int) -> list[WebResult]:
    today = dt.date.today().isoformat()
    return [
        WebResult(
            title=f"[DEMO] Resultado simulado para: {query}",
            url="https://example.com/demo",
            snippet=(
                "Resultado simulado. Configura BRAVE_SEARCH_API_KEY, "
                "TAVILY_API_KEY o PERPLEXITY_API_KEY y DEMO_MODE=false para "
                "obtener opciones de mercado reales y actualizadas."
            ),
            published=today,
            source="DEMO",
            provider="demo",
        )
    ][:max_results]


def _tavily_country(country: str) -> str:
    mapping = {"ES": "spain", "US": "united states", "GB": "united kingdom"}
    return mapping.get(country.upper(), country.lower())
