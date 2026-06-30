"""Pydantic-Settings configuration for the PE Investment Platform.

All environment variables are documented here.  Override via a ``.env`` file
or by exporting variables before starting the application.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
    )

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    max_llm_tokens_per_run: int = 4000

    # ── External data / search API keys ────────────────────────────────────────
    tavily_api_key: str | None = None
    companies_house_api_key: str | None = None
    # Explorium — Business firmographics (revenue, employee range, industry, HQ).
    # Optional/opt-in; the competitive agent skips Explorium when this is unset.
    # (Wikidata and GLEIF need no key and are always available.)
    explorium_api_key: str | None = None

    # ── SEC EDGAR ──────────────────────────────────────────────────────────────
    # SEC requires a descriptive User-Agent with real contact info on every request.
    sec_user_agent: str = "PE Platform Bot (contact@peplatform.local)"

    # ── Application ──────────────────────────────────────────────────────────
    environment: str = "dev"
    allowed_origins: str = ""

    # ── Scheduler ────────────────────────────────────────────────────────────
    scheduler_timezone: str = "UTC"
    nightly_ingest_hour: int = 3
    nightly_ingest_minute: int = 0


# Global singleton — imported by modules that need configuration.
settings = Settings()
