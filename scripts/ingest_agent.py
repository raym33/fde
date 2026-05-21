#!/usr/bin/env python3
"""Scheduled ingestion agent for documents and curated knowledge updates.

This script is intended for self-hosted deployments where the operator wants a
nightly or periodic sync from allowlisted local folders into VirtuDirector IA.
"""
from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path
from urllib import error, parse, request


SUPPORTED_DOCUMENTS = {".txt", ".md", ".markdown", ".docx", ".pdf"}
KNOWLEDGE_HINTS = {"intel", "update", "trend", "news", "market", "roadmap"}


def _multipart_form(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----VirtuDirectorIngestAgentBoundary"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), boundary


def _post_file(base_url: str, endpoint: str, file_path: Path, headers: dict[str, str], fields: dict[str, str]) -> str:
    body, boundary = _multipart_form(fields, "file", file_path)
    req = request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **headers,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=180) as response:
        return response.read().decode("utf-8")


def _is_knowledge_file(path: Path) -> bool:
    lowered = path.name.lower()
    return any(token in lowered for token in KNOWLEDGE_HINTS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest allowlisted local files into VirtuDirector IA.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--user-id", default="ingest-agent")
    parser.add_argument("--client-name", required=True)
    parser.add_argument("--source-dir", action="append", required=True, help="Allowlisted source directory. Can be passed multiple times.")
    parser.add_argument("--knowledge-source-type", default="scheduled_ingest")
    args = parser.parse_args()

    headers = {
        "X-Tenant-Id": args.tenant_id,
        "X-User-Id": args.user_id,
        "X-Client-Name": args.client_name,
    }

    for source in args.source_dir:
        source_dir = Path(source).expanduser().resolve()
        if not source_dir.exists():
            raise SystemExit(f"Source directory does not exist: {source_dir}")
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_DOCUMENTS:
                continue
            try:
                if _is_knowledge_file(path):
                    payload = _post_file(
                        args.base_url,
                        "/knowledge/updates",
                        path,
                        headers,
                        {
                            "title": path.stem.replace("-", " "),
                            "source_type": args.knowledge_source_type,
                            "scope": "global",
                        },
                    )
                    print(f"[knowledge] {path.name}: {payload[:200]}")
                else:
                    payload = _post_file(
                        args.base_url,
                        "/documents",
                        path,
                        headers,
                        {"title": path.name},
                    )
                    print(f"[document] {path.name}: {payload[:200]}")
            except error.HTTPError as exc:
                print(f"[error] {path.name}: HTTP {exc.code}")
            except Exception as exc:  # noqa: BLE001
                print(f"[error] {path.name}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
