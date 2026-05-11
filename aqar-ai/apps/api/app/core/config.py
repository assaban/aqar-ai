"""
Aqar.ai - Application Configuration
===================================
Type-safe settings loaded from environment variables.
Uses pydantic-settings for validation and defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "aqar-ai"
    app_env: str = "development"  # development | staging | production
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://aqar:aqar_dev_password@localhost:5432/aqar_db"
    database_url_sync: str = "postgresql://aqar:aqar_dev_password@localhost:5432/aqar_db"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ──
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Meilisearch ──
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_master_key: str = "aqar_meili_dev_key"

    # ── API ──
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: str = "http://localhost:3000,http://localhost:8081"

    # ── Anthropic Claude ──
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096

    # ── Whisper ──
    whisper_model: str = "large-v3"
    whisper_device: str = "cpu"
    whisper_language: str = "ar"

    # ── Geocoding ──
    geocoding_provider: str = "nominatim"
    google_maps_api_key: str = ""
    nominatim_user_agent: str = "aqar-ai-dev"

    # ── Video Ingestion ──
    youtube_api_key: str = ""
    max_video_duration_minutes: int = 30
    download_path: str = "/tmp/aqar/downloads"

    # ── Monitoring ──
    sentry_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (singleton)."""
    return Settings()
