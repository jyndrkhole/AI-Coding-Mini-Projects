"""Environment-backed settings. Paths and model names are never fixed in business code."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"
    openai_base_url: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sqlite_path: str = "./data/sqlite/tripwise.db"
    chroma_path: str = "./data/chroma"
    upload_path: str = "./data/uploads"
    knowledge_path: str = "./data/knowledge"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    similarity_threshold: float = 0.28
    retrieval_k: int = 4
    chunk_size: int = 800
    chunk_overlap: int = 120
    max_tool_steps: int = 10
    agent_timeout_seconds: int = 90
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_max_bytes: int = 5_000_000
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 600
    chroma_collection: str = "trip_knowledge"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def sqlite_file(self) -> Path:
        return resolve_path(self.sqlite_path)

    @property
    def chroma_dir(self) -> Path:
        return resolve_path(self.chroma_path)

    @property
    def upload_dir(self) -> Path:
        return resolve_path(self.upload_path)

    @property
    def knowledge_dir(self) -> Path:
        return resolve_path(self.knowledge_path)

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key.strip() or self.openai_api_key.strip())

    @property
    def llm_provider(self) -> str:
        if self.groq_api_key.strip():
            return "groq"
        if self.openai_api_key.strip():
            return "openai"
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
