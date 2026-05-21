from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from app.config import get_settings


class PremiumCLIError(RuntimeError):
    pass


def _command_for(provider: str) -> str:
    settings = get_settings()
    if provider == "claude_cli":
        return settings.claude_cli_command
    if provider == "codex_cli":
        return settings.codex_cli_command
    raise PremiumCLIError(f"Unsupported CLI provider: {provider}")


def _args_for(provider: str, prompt: str) -> list[str]:
    command = _command_for(provider)
    if provider == "claude_cli":
        return [command, "-p", prompt, "--output-format", "json"]
    if provider == "codex_cli":
        return [command, "exec", prompt]
    raise PremiumCLIError(f"Unsupported CLI provider: {provider}")


def _flatten_messages(messages: list[dict]) -> str:
    parts = []
    for item in messages:
        role = item.get("role", "user")
        content = item.get("content", "")
        parts.append(f"[{role.upper()}]\n{content}")
    return "\n\n".join(parts)


def _parse_output(provider: str, output: str) -> str:
    text = output.strip()
    if not text:
        return ""
    if provider == "claude_cli":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return (
                    data.get("result")
                    or data.get("content")
                    or data.get("text")
                    or text
                )
        except json.JSONDecodeError:
            return text
    return text


async def complete(provider: str, messages: list[dict], timeout: float | None = None) -> str:
    settings = get_settings()
    sandbox_dir = settings.premium_sandbox_path
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    prompt = _flatten_messages(messages)
    args = _args_for(provider, prompt)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(sandbox_dir),
    )
    out, err = await asyncio.wait_for(
        proc.communicate(),
        timeout=timeout or settings.premium_cli_timeout_seconds,
    )
    if proc.returncode != 0:
        raise PremiumCLIError((err or out).decode("utf-8", errors="ignore")[:500])
    return _parse_output(provider, out.decode("utf-8", errors="ignore"))


async def status(provider: str) -> dict:
    settings = get_settings()
    command = _command_for(provider)
    binary = shutil.which(command)
    if not binary:
        return {
            "provider": provider,
            "available": False,
            "authenticated": False,
            "binary": None,
            "detail": f"Binary not found: {command}",
            "sandbox_dir": str(settings.premium_sandbox_path),
        }
    return {
        "provider": provider,
        "available": True,
        "authenticated": None,
        "binary": binary,
        "detail": "Binary found. Authentication status cannot be verified without executing a real command.",
        "sandbox_dir": str(settings.premium_sandbox_path),
    }
