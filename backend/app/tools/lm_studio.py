"""LM Studio OpenAI-compatible client.

LM Studio exposes `/v1/models`, `/v1/chat/completions` and, when an embedding
model is loaded, `/v1/embeddings`. The base URL is configurable, so the same
code can point to this Mac (`127.0.0.1`) or another machine on the LAN.
"""
from __future__ import annotations

import httpx

from app.config import get_settings


class LMStudioError(RuntimeError):
    pass


async def list_models(base_url: str | None = None) -> list[dict]:
    settings = get_settings()
    url = (base_url or settings.lm_studio_base_url).rstrip("/")
    data = await _request_json("GET", f"{url}/models")
    return data.get("data", [])


async def status() -> dict:
    settings = get_settings()
    nodes = []
    for base_url in settings.lm_studio_base_urls:
        try:
            models = await list_models(base_url)
            nodes.append(
                {
                    "base_url": base_url,
                    "available": True,
                    "models": [m.get("id") for m in models],
                }
            )
        except Exception as exc:  # noqa: BLE001
            nodes.append(
                {
                    "base_url": base_url,
                    "available": False,
                    "error": str(exc),
                    "models": [],
                }
            )
    return {
        "enabled": settings.local_llm_enabled,
        "provider": settings.local_llm_provider,
        "chat_model": settings.lm_studio_chat_model,
        "embedding_model": settings.lm_studio_embedding_model,
        "nodes": nodes,
    }


async def chat_completion(
    *,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    response_format: dict | None = None,
) -> str:
    settings = get_settings()
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if response_format:
        body["response_format"] = _normalize_response_format(response_format)

    last_error: Exception | None = None
    for base_url in settings.lm_studio_base_urls:
        try:
            data = await _chat_request(base_url, body)
            return data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not response_format:
                continue
            # Some LM Studio model/runtime combinations reject structured
            # output. The verifier prompt still asks for strict JSON, so
            # retrying as plain text is safer than breaking the whole CAIO
            # response.
            text_body = dict(body)
            text_body.pop("response_format", None)
            try:
                data = await _chat_request(base_url, text_body)
                return data.get("choices", [{}])[0].get("message", {}).get("content") or ""
            except Exception as retry_exc:  # noqa: BLE001
                last_error = retry_exc
                continue
    raise LMStudioError(f"No LM Studio node completed chat request: {last_error}")


async def stream_chat_completion(
    *,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
):
    # Keep this simple for now: get the LM Studio response and stream
    # word-by-word through our existing SSE layer. We can switch to native SSE
    # later.
    text = await chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    for token in text.split(" "):
        yield token + " "


async def embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
    settings = get_settings()
    body = {
        "model": model or settings.lm_studio_embedding_model,
        "input": texts,
    }
    last_error: Exception | None = None
    for base_url in settings.lm_studio_base_urls:
        try:
            data = await _request_json(
                "POST",
                f"{base_url.rstrip('/')}/embeddings",
                json=body,
                headers=_headers(),
            )
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise LMStudioError(f"No LM Studio node completed embedding request: {last_error}")


async def test_prompt(prompt: str = "Responde en una frase: listo.") -> dict:
    settings = get_settings()
    model = settings.lm_studio_chat_model
    content = await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.1,
        max_tokens=120,
    )
    return {"model": model, "response": content}


async def _request_json(method: str, url: str, **kwargs) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.lm_studio_timeout_seconds) as client:
        response = await client.request(method, url, **kwargs)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise LMStudioError(f"LM Studio HTTP {response.status_code}: {response.text[:300]}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise LMStudioError("LM Studio returned non-JSON response") from exc


def _headers() -> dict:
    settings = get_settings()
    return {"Authorization": f"Bearer {settings.lm_studio_api_key}"}


async def _chat_request(base_url: str, body: dict) -> dict:
    return await _request_json(
        "POST",
        f"{base_url.rstrip('/')}/chat/completions",
        json=body,
        headers=_headers(),
    )


def _normalize_response_format(response_format: dict) -> dict:
    if response_format.get("type") != "json_object":
        return response_format
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "virtudirector_json_response",
            "strict": False,
            "schema": {"type": "object"},
        },
    }
