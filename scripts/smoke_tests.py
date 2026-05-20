#!/usr/bin/env python3
"""End-to-end smoke tests for a running VirtuDirector IA backend.

These tests intentionally hit the live HTTP API because the product depends on
runtime wiring: LM Studio, SSE chat, document upload, labs persistence and the
static app shell.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class TestResult:
    name: str
    ok: bool
    detail: str
    elapsed_ms: int


class SmokeClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(
            self.base_url + path, timeout=self.timeout
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_text(self, path: str) -> str:
        with urllib.request.urlopen(
            self.base_url + path, timeout=self.timeout
        ) as response:
            return response.read().decode("utf-8")

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json_as_tenant(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Tenant-Id": "smoke-tenant",
                "X-User-Id": "smoke-tests",
                "X-Client-Name": "Smoke SL",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_multipart_text_document(self) -> dict[str, Any]:
        boundary = "----VirtuDirectorSmokeBoundary"
        content = (
            "--{b}\r\n"
            'Content-Disposition: form-data; name="title"\r\n\r\n'
            "Smoke test policy\r\n"
            "--{b}\r\n"
            'Content-Disposition: form-data; name="file"; filename="smoke.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "Politica IA smoke test. Responsable humano, RAG y EU AI Act.\r\n"
            "--{b}--\r\n"
        ).format(b=boundary).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/documents",
            data=content,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Tenant-Id": "smoke-tenant",
                "X-User-Id": "smoke-tests",
                "X-Client-Name": "Smoke SL",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_knowledge_update(self) -> dict[str, Any]:
        boundary = "----VirtuDirectorKnowledgeSmokeBoundary"
        content = (
            "--{b}\r\n"
            'Content-Disposition: form-data; name="title"\r\n\r\n'
            "Smoke AI intelligence update\r\n"
            "--{b}\r\n"
            'Content-Disposition: form-data; name="source_type"\r\n\r\n'
            "smoke_daily_update\r\n"
            "--{b}\r\n"
            'Content-Disposition: form-data; name="scope"\r\n\r\n'
            "global\r\n"
            "--{b}\r\n"
            'Content-Disposition: form-data; name="file"; filename="ai-intel-smoke.md"\r\n'
            "Content-Type: text/markdown\r\n\r\n"
            "# AI Intel Smoke\n\n"
            "RAG con BM25, embeddings y reranker mejora recuperación. "
            "El routing de modelos locales reduce costes para pymes españolas. "
            "Revisar EU AI Act, licencias y trazabilidad antes de producción.\r\n"
            "--{b}--\r\n"
        ).format(b=boundary).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/knowledge/updates",
            data=content,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Tenant-Id": "platform",
                "X-User-Id": "smoke-technician",
                "X-Client-Name": "VirtuDirector Platform",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_chat_sse(self, message: str) -> list[dict[str, Any]]:
        data = json.dumps({"message": message}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Tenant-Id": "smoke-tenant",
                "X-User-Id": "smoke-tests",
                "X-Client-Name": "Smoke SL",
            },
            method="POST",
        )
        events: list[dict[str, Any]] = []
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        for block in raw.split("\n\n"):
            line = next((item for item in block.splitlines() if item.startswith("data: ")), None)
            if line:
                events.append(json.loads(line[6:]))
        return events


def run_test(name: str, fn) -> TestResult:
    start = time.perf_counter()
    try:
        detail = fn()
        ok = True
    except Exception as exc:  # noqa: BLE001
        detail = f"{type(exc).__name__}: {exc}"
        ok = False
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return TestResult(name=name, ok=ok, detail=str(detail), elapsed_ms=elapsed_ms)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--skip-chat", action="store_true")
    args = parser.parse_args()
    client = SmokeClient(args.base_url, args.timeout)

    tests = [
        (
            "healthz",
            lambda: (
                lambda data: (
                    require(data["status"] == "ok", "healthz status is not ok"),
                    data["service"],
                )[1]
            )(client.get_json("/healthz")),
        ),
        (
            "health runtime",
            lambda: (
                lambda data: (
                    require(data["status"] == "ok", "health status is not ok"),
                    require(data["lm_studio"]["enabled"] is True, "LM Studio disabled"),
                    require(data["models"]["premium"], "premium model missing"),
                    f"premium={data['models']['premium']}",
                )[3]
            )(client.get_json("/health")),
        ),
        (
            "static app shell",
            lambda: (
                lambda html: (
                    require("VirtuDirector IA" in html, "app shell missing product name"),
                    require("CAIO Chat" in html, "app shell missing chat"),
                    "app shell ok",
                )[2]
            )(client.get_text("/app")),
        ),
        (
            "LM Studio status",
            lambda: (
                lambda data: (
                    require(any(n.get("available") for n in data["nodes"]), "no LM Studio node available"),
                    ", ".join(data["nodes"][0].get("models", [])),
                )[1]
            )(client.get_json("/tools/lm-studio/status")),
        ),
        (
            "LM Studio completion",
            lambda: (
                lambda data: (
                    require(data["response"].strip(), "empty LM Studio response"),
                    data["response"].strip()[:80],
                )[1]
            )(
                client.get_json(
                    "/tools/lm-studio/test?"
                    + urllib.parse.urlencode({"prompt": "responde solo con la palabra listo"})
                )
            ),
        ),
        (
            "web search status",
            lambda: (
                lambda data: (
                    require("provider" in data, "provider missing"),
                    f"provider={data['provider']}",
                )[1]
            )(client.get_json("/tools/web-search/status")),
        ),
        (
            "document parser status",
            lambda: (
                lambda data: (
                    require(data["pdf_text"] is True, "PDF parser unavailable"),
                    require(data["docx"] is True, "DOCX parser unavailable"),
                    "pdf/docx ok",
                )[2]
            )(client.get_json("/documents/status")),
        ),
        (
            "document upload + RAG ingest",
            lambda: (
                lambda data: (
                    require(data["chunks"] >= 1, "no chunks created"),
                    require(data["parser"].startswith("text"), "unexpected parser"),
                    f"chunks={data['chunks']}",
                )[2]
            )(client.post_multipart_text_document()),
        ),
        (
            "knowledge update upload + compact",
            lambda: (
                lambda data: (
                    require(data["status"] in {"accepted", "duplicate"}, "knowledge update rejected"),
                    require(data["brief"]["summary"], "compact summary missing"),
                    require(data["brief"]["tags"], "tags missing"),
                    f"status={data['status']} tags={','.join(data['brief']['tags'])}",
                )[3]
            )(client.post_knowledge_update()),
        ),
        (
            "knowledge brief retrieval",
            lambda: (
                lambda data: (
                    require(data["briefs"], "no knowledge briefs returned"),
                    f"briefs={len(data['briefs'])}",
                )[1]
            )(client.get_json("/knowledge/briefs?q=rag%20costes%20pymes&limit=3")),
        ),
        (
            "opportunity diagnosis",
            lambda: (
                lambda data: (
                    require(data["diagnosis"]["top_opportunities"], "no opportunities returned"),
                    require(
                        data["diagnosis"]["top_opportunities"][0]["score"]["total"] > 0,
                        "opportunity score missing",
                    ),
                    require("Mapa de oportunidades IA" in data["markdown"], "markdown report missing"),
                    (
                        f"top={data['diagnosis']['top_opportunities'][0]['id']} "
                        f"score={data['diagnosis']['top_opportunities'][0]['score']['total']}"
                    ),
                )[3]
            )(
                client.post_json_as_tenant(
                    "/opportunities/diagnose",
                    {
                        "question": "dónde debería implementar IA primero en una pyme de 500 empleados",
                        "employee_count": 500,
                    },
                )
            ),
        ),
        (
            "labs catalog",
            lambda: (
                lambda data: (
                    require(len(data["labs"]) >= 6, "expected at least 6 labs"),
                    f"labs={len(data['labs'])}",
                )[1]
            )(client.get_json("/labs/catalog")),
        ),
        (
            "run RAG lab",
            lambda: (
                lambda data: (
                    require(data["runs"], "no lab run returned"),
                    require("baseline" in data["runs"][0]["metrics"], "RAG baseline metrics missing"),
                    require("candidate" in data["runs"][0]["metrics"], "RAG candidate metrics missing"),
                    require(
                        data["runs"][0]["status"] in {"report_proposed", "no_material_improvement"},
                        "unexpected RAG lab status",
                    ),
                    (
                        f"status={data['runs'][0]['status']} "
                        f"improvement={data['runs'][0]['improvement_pct']}%"
                    ),
                )[4]
            )(client.post_json("/labs/experiments/run", {"lab_id": "rag_grounding", "triggered_by": "smoke"})),
        ),
        (
            "feature flags",
            lambda: (
                lambda data: (
                    require("feature_flags" in data, "feature flags missing"),
                    f"flags={len(data['feature_flags'])}",
                )[1]
            )(client.get_json("/labs/feature-flags")),
        ),
    ]

    if not args.skip_chat:
        tests.append(
            (
                "chat SSE via local LLM",
                lambda: (
                    lambda events: (
                        require(any(e["type"] == "token" for e in events), "no token events"),
                        require(any(e["type"] == "final" for e in events), "no final event"),
                        f"events={len(events)}",
                    )[2]
                )(client.post_chat_sse("responde en una frase: test de humo")),
            )
        )

    results = [run_test(name, fn) for name, fn in tests]
    width = max(len(result.name) for result in results)
    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"{marker} {result.name:<{width}} {result.elapsed_ms:>6}ms  {result.detail}")

    failed = [result for result in results if not result.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"Backend not reachable: {exc}", file=sys.stderr)
        raise SystemExit(2)
