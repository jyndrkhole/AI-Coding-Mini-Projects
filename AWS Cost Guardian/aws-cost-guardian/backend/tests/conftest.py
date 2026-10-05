from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MOCK_DATA_DIR = PROJECT_ROOT / "mock_data"


def build_client(monkeypatch: pytest.MonkeyPatch, database_path: Path, mock_aws: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("MOCK_AWS", mock_aws)
    monkeypatch.setenv("MOCK_DATA_DIR", str(MOCK_DATA_DIR))
    from app.core.config import get_settings
    from app.db.database import reset_engine

    get_settings.cache_clear()
    reset_engine()
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    test_client = build_client(monkeypatch, tmp_path / "demo.db", "true")
    with test_client:
        yield test_client
    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()
