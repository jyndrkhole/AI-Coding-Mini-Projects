"""Runtime settings. Environment variables override the defaults."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "aws_cost_guardian.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AWS Cost Guardian"
    app_version: str = "0.1.0"
    mock_aws: bool = True
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    mock_data_dir: str | None = None
    aws_profile: str | None = None
    aws_region: str = "us-east-1"
    aws_role_arn: str | None = None
    aws_external_id: str | None = None
    ai_provider: str = "ollama"
    api_cors_origins: str = "http://localhost:5173"

    def resolved_mock_data_dir(self) -> Path:
        if self.mock_data_dir:
            return Path(self.mock_data_dir)
        return PROJECT_ROOT / "mock_data"

    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
