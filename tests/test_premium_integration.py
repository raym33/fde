from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import get_settings
from app.core import escalation
from app.core.model_router import ModelRouter, _redact_messages
from app.core.schemas import Intent, RetrievedChunk, VerifierVerdict
from app.tools import cli_provider


def _reset_settings(monkeypatch, **env: str) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_provider_for_premium_can_use_cli(monkeypatch) -> None:
    _reset_settings(
        monkeypatch,
        LOCAL_LLM_ENABLED="true",
        LOCAL_LLM_PROVIDER="lmstudio",
        PREMIUM_PROVIDER="claude_cli",
    )
    router = ModelRouter()
    assert router.provider_for("cheap") == "lmstudio"
    assert router.provider_for("medium") == "lmstudio"
    assert router.provider_for("premium") == "claude_cli"


def test_redact_messages_removes_pii() -> None:
    safe_messages, pii_map = _redact_messages(
        [{"role": "user", "content": "Email john@example.com and IBAN ES7620770024003102575766"}]
    )
    assert "[EMAIL_1]" in safe_messages[0]["content"]
    assert "[IBAN_1]" in safe_messages[0]["content"]
    assert pii_map["[EMAIL_1]"] == "john@example.com"


def test_should_escalate_only_when_enabled(monkeypatch) -> None:
    _reset_settings(
        monkeypatch,
        ESCALATION_ENABLED="true",
        PREMIUM_PROVIDER="anthropic_api",
        ESCALATION_ALLOWED_INTENTS="strategy,grc",
        ESCALATION_ALLOW_SENSITIVE="false",
        LOCAL_CONTEXT_LIMIT="10",
    )
    chunks = [RetrievedChunk(chunk_id="c1", document_id="d1", text="ordinary support context", score=1.0, metadata={})]
    verdict = VerifierVerdict(approved=False, issues=[{"type": "test"}], revised_answer=None)
    assert escalation.should_escalate(
        intent=Intent.STRATEGY,
        message="Please answer this with a premium version",
        verdict=verdict,
        chunks=chunks,
    )


def test_should_not_escalate_sensitive_content_by_default(monkeypatch) -> None:
    _reset_settings(
        monkeypatch,
        ESCALATION_ENABLED="true",
        PREMIUM_PROVIDER="anthropic_api",
        ESCALATION_ALLOWED_INTENTS="strategy,grc",
        ESCALATION_ALLOW_SENSITIVE="false",
    )
    chunks = [RetrievedChunk(chunk_id="c1", document_id="d1", text="historia clínica del paciente", score=1.0, metadata={})]
    verdict = VerifierVerdict(approved=False, issues=[{"type": "test"}], revised_answer=None)
    assert not escalation.should_escalate(
        intent=Intent.GRC,
        message="Review this policy",
        verdict=verdict,
        chunks=chunks,
    )
    decision = escalation.escalation_decision(
        intent=Intent.GRC,
        message="Review this policy",
        verdict=verdict,
        chunks=chunks,
    )
    assert decision.sensitivity_level == "regulated"
    assert decision.blocked_reason is not None


def test_cli_status_reports_missing_binary(monkeypatch) -> None:
    _reset_settings(monkeypatch, CLAUDE_CLI_COMMAND="missing-claude-binary")
    status = asyncio.run(cli_provider.status("claude_cli"))
    assert status["available"] is False
    assert status["binary"] is None


def test_demo_mode_does_not_require_cli(monkeypatch) -> None:
    _reset_settings(
        monkeypatch,
        DEMO_MODE="true",
        LOCAL_LLM_ENABLED="false",
        PREMIUM_PROVIDER="claude_cli",
    )

    async def _fail(*args, **kwargs):  # noqa: ANN001, ANN003
        raise AssertionError("CLI provider should not be called in demo mode")

    monkeypatch.setattr(cli_provider, "complete", _fail)
    router = ModelRouter()
    text = asyncio.run(
        router.complete(
            messages=[{"role": "user", "content": "Need a premium answer"}],
            tier="premium",
        )
    )
    assert "[DEMO" in text
