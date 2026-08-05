"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime settings for the Schema Validator API."""

    app_name: str = "API Schema Validation Portal"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    max_payload_size_mb: int = 20
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Privacy defaults: keep all schema/response data on this machine.
    privacy_mode: str = "strict"  # strict | standard
    allow_remote_schema_fetch: bool = False
    allow_cloud_llm: bool = False
    allow_local_llm: bool = True
    log_payloads: bool = False

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_payload_bytes(self) -> int:
        return self.max_payload_size_mb * 1024 * 1024

    @property
    def is_strict_privacy(self) -> bool:
        return self.privacy_mode.lower() == "strict"

    @property
    def remote_schema_fetch_enabled(self) -> bool:
        return False if self.is_strict_privacy else self.allow_remote_schema_fetch

    @property
    def cloud_llm_enabled(self) -> bool:
        return False if self.is_strict_privacy else self.allow_cloud_llm

    @property
    def payload_logging_enabled(self) -> bool:
        return False if self.is_strict_privacy else self.log_payloads


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
