"""Central application settings based on pydantic-settings.

All options are loaded from environment variables or `backend/.env`.
See `backend/.env.example` for defaults and comments.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "virtudirector_labs.sqlite3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Runtime mode
    demo_mode: bool = True
    environment: str = "development"

    # Provider keys. LiteLLM reads the standard environment variables, but they
    # are exposed here for validation and runtime status reporting.
    deepinfra_api_key: str | None = None
    together_api_key: str | None = None
    fireworks_api_key: str | None = None
    groq_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # External tools
    search_provider: str = "auto"  # auto | brave | tavily | perplexity | demo
    brave_search_api_key: str | None = None
    tavily_api_key: str | None = None
    perplexity_api_key: str | None = None
    web_search_timeout_seconds: float = 10.0
    web_search_cache_ttl_seconds: int = 900
    web_search_default_country: str = "ES"
    web_search_default_language: str = "es"

    # Model identifiers by tier
    model_router_cheap: str = "deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct"
    model_router_medium: str = "deepinfra/Qwen/Qwen3-235B-A22B"
    model_router_premium: str = "anthropic/claude-sonnet-4-6"
    model_embeddings: str = "deepinfra/BAAI/bge-m3"

    # Local / LAN inference (LM Studio OpenAI-compatible server)
    local_llm_enabled: bool = False
    local_llm_provider: str = "lmstudio"
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    lm_studio_api_key: str = "lm-studio"
    lm_studio_timeout_seconds: float = 120.0
    lm_studio_chat_model: str = "gemma-4-26b-a4b-it-mlx"
    lm_studio_model_cheap: str | None = None
    lm_studio_model_medium: str | None = None
    lm_studio_model_premium: str | None = None
    lm_studio_embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
    lm_studio_remote_base_urls: str = ""  # comma-separated http://host:1234/v1
    local_embedding_fallback: bool = True

    # Infrastructure
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/virtudirector"
    )
    redis_url: str = "redis://localhost:6379/0"
    labs_sqlite_path: str | None = None

    # Observability
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Auth and limits
    jwt_secret: str = "dev-secret-change-me"
    admin_basic_username: str = "admin"
    admin_basic_password: str = "change-me-admin"
    max_tokens_per_request: int = 8000
    max_agent_steps: int = 8
    data_region: str = "eu"

    @property
    def has_any_model_key(self) -> bool:
        return any(
            [
                self.deepinfra_api_key,
                self.together_api_key,
                self.fireworks_api_key,
                self.groq_api_key,
                self.anthropic_api_key,
                self.openai_api_key,
            ]
        )

    @property
    def has_any_search_key(self) -> bool:
        return any(
            [
                self.brave_search_api_key,
                self.tavily_api_key,
                self.perplexity_api_key,
            ]
        )

    @property
    def lm_studio_base_urls(self) -> list[str]:
        urls = [self.lm_studio_base_url]
        urls.extend(
            url.strip()
            for url in self.lm_studio_remote_base_urls.split(",")
            if url.strip()
        )
        out = []
        for url in urls:
            out.append(url.rstrip("/"))
        return out

    @property
    def sqlite_path(self) -> Path:
        if self.labs_sqlite_path:
            return Path(self.labs_sqlite_path).expanduser().resolve()
        return DEFAULT_SQLITE_PATH


@lru_cache
def get_settings() -> Settings:
    return Settings()
