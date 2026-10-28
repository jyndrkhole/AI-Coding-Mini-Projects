"""Runtime configuration. Secrets come from the environment, never from source."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
ENV_FILES = (ROOT / ".env", ROOT / "backend" / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(path) for path in ENV_FILES if path.exists()) or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    agent_timeout_seconds: float = 90
    data_timeout_seconds: float = 40
    news_lookback_days: int = 30
    cache_ttl_seconds: int = 900
    database_path: str = str(ROOT / "backend" / "data" / "analyses.db")

    @property
    def provider_name(self) -> str:
        return self.llm_provider.strip().lower()

    def llm_status(self) -> dict[str, str | bool]:
        provider = self.provider_name
        if provider == "groq":
            return {
                "provider": "groq",
                "model": self.groq_model,
                "configured": bool(self.groq_api_key.strip()),
                "message": "" if self.groq_api_key.strip() else "GROQ_API_KEY is missing.",
            }
        if provider == "openai":
            return {
                "provider": "openai",
                "model": self.openai_model,
                "configured": bool(self.openai_api_key.strip()),
                "message": "" if self.openai_api_key.strip() else "OPENAI_API_KEY is missing.",
            }
        if provider:
            return {
                "provider": provider,
                "model": "",
                "configured": False,
                "message": "LLM_PROVIDER must be 'groq' or 'openai'.",
            }
        return {
            "provider": "",
            "model": "",
            "configured": False,
            "message": "LLM_PROVIDER is unset. Ratios, DCF, risk, and the rating still run. Commentary is rule-based.",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
