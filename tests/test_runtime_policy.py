from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.db import init_db
from app.core.model_router import ModelRouter
from app.core.runtime_policy import activate_tenant_policy, resolve_tenant_policy, upsert_tenant_policy
from app.main import app


def _reset_settings(monkeypatch, **env: str) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_tenant_runtime_policy_overrides_default_provider(monkeypatch, tmp_path) -> None:
    _reset_settings(
        monkeypatch,
        LABS_SQLITE_PATH=str(tmp_path / "runtime-policy.sqlite3"),
        LOCAL_LLM_ENABLED="true",
        LOCAL_LLM_PROVIDER="lmstudio",
        PREMIUM_PROVIDER="lmstudio",
        ESCALATION_ENABLED="false",
    )
    init_db()

    upsert_tenant_policy(
        "tenant-a",
        updated_by="tester",
        premium_provider="claude_cli",
        escalation_enabled=True,
        escalation_allow_sensitive=False,
        escalation_allowed_intents="strategy,grc",
    )

    router = ModelRouter()
    with activate_tenant_policy("tenant-a"):
        assert router.provider_for("premium") == "claude_cli"
        policy = resolve_tenant_policy("tenant-a")
        assert policy.source == "tenant_override"
        assert policy.escalation_enabled is True

    with activate_tenant_policy("tenant-b"):
        assert router.provider_for("premium") == "lmstudio"
        policy = resolve_tenant_policy("tenant-b")
        assert policy.source == "default"
        assert policy.escalation_enabled is False


def test_runtime_policy_routes_round_trip(monkeypatch, tmp_path) -> None:
    _reset_settings(
        monkeypatch,
        LABS_SQLITE_PATH=str(tmp_path / "runtime-policy-api.sqlite3"),
        LOCAL_LLM_ENABLED="true",
        PREMIUM_PROVIDER="lmstudio",
        CODEX_CLI_COMMAND="missing-codex-binary",
    )
    init_db()
    client = TestClient(app)
    headers = {
        "X-Tenant-Id": "tenant-runtime",
        "X-User-Id": "tester",
        "X-Client-Name": "Tenant Runtime SL",
    }

    response = client.post(
        "/tools/runtime-policy",
        headers=headers,
        json={
            "premium_provider": "codex_cli",
            "escalation_enabled": True,
            "escalation_allow_sensitive": False,
            "escalation_allowed_intents": "strategy,grc,deliverable",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["effective"]["premium_provider"] == "codex_cli"
    assert payload["effective"]["source"] == "tenant_override"

    status = client.get("/tools/premium/status", headers=headers)
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["provider"] == "codex_cli"
    assert status_payload["policy_source"] == "tenant_override"
