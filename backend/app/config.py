"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


def _resolve_project_path(value: Path | str) -> Path:
    """Resolve relative paths against the project root (not process cwd)."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve()


def _normalize_sqlite_url(url: str) -> str:
    """Make SQLite URLs absolute so they work regardless of process cwd."""
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if url.startswith(prefix):
            raw = url[len(prefix) :]
            # Absolute Unix path already encoded as sqlite:////abs/path
            if raw.startswith("/"):
                return url
            db_path = _resolve_project_path(raw)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{prefix}{db_path}"
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Email Intelligence Platform"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = f"sqlite+aiosqlite:///{ROOT_DIR / 'data' / 'email_ai.db'}"

    llm_provider: Literal["groq", "ollama"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.4
    llm_max_tokens: int = 4096

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    embedding_provider: Literal["local", "ollama"] = "local"
    embedding_model: str = "onnx-minilm-l6-v2"
    ollama_embedding_model: str = "nomic-embed-text"

    chunk_size: int = 800
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    vector_db_path: Path = Field(default=ROOT_DIR / "vector_db")
    upload_dir: Path = Field(default=ROOT_DIR / "uploads")
    workspaces_dir: Path = Field(default=ROOT_DIR / "workspaces")
    prompts_dir: Path = Field(default=ROOT_DIR / "prompts")
    logs_dir: Path = Field(default=ROOT_DIR / "logs")
    data_dir: Path = Field(default=ROOT_DIR / "data")

    @field_validator(
        "vector_db_path",
        "upload_dir",
        "workspaces_dir",
        "prompts_dir",
        "logs_dir",
        "data_dir",
        mode="before",
    )
    @classmethod
    def resolve_paths(cls, value: Path | str) -> Path:
        return _resolve_project_path(value)

    @model_validator(mode="after")
    def normalize_database_url(self) -> "Settings":
        self.database_url = _normalize_sqlite_url(self.database_url)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_directories(self) -> None:
        for path in (
            self.vector_db_path,
            self.upload_dir,
            self.workspaces_dir,
            self.prompts_dir,
            self.logs_dir,
            self.data_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
