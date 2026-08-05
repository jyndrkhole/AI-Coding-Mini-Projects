"""Privacy / local-only boundary tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.core.config import clear_settings_cache, get_settings
from backend.core.privacy import PrivacyError, assert_ollama_is_local, assert_url_safe_for_fetch
from backend.llm.providers import get_provider
from backend.main import app
from backend.models.schemas import SchemaLoadRequest, SchemaSourceType
from backend.services.schema_loader import SchemaLoaderService

client = TestClient(app)


def test_health_exposes_strict_privacy():
    clear_settings_cache()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    privacy = resp.json()["privacy"]
    assert privacy["mode"] == "strict"
    assert privacy["remote_schema_fetch"] is False
    assert privacy["cloud_llm"] is False
    assert privacy["payload_logging"] is False


def test_remote_url_fetch_blocked():
    clear_settings_cache()
    resp = client.post(
        "/api/schema/load",
        data={
            "source_type": "url",
            "url": "https://example.com/openapi.yaml",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "privacy" in (body.get("error") or "").lower() or "disabled" in (
        body.get("error") or ""
    ).lower()


@pytest.mark.asyncio
async def test_loader_blocks_url_in_strict_mode():
    clear_settings_cache()
    service = SchemaLoaderService()
    result = await service.load(
        SchemaLoadRequest(
            source_type=SchemaSourceType.URL,
            url="https://example.com/schema.json",
        )
    )
    assert result.success is False
    assert "local" in (result.error or "").lower() or "disabled" in (result.error or "").lower()


def test_cloud_llm_blocked():
    clear_settings_cache()
    settings = get_settings()
    with pytest.raises(PrivacyError):
        get_provider("groq", settings)


def test_ssrf_blocks_private_ip():
    with pytest.raises(PrivacyError):
        assert_url_safe_for_fetch("http://127.0.0.1/secret")
    with pytest.raises(PrivacyError):
        assert_url_safe_for_fetch("http://169.254.169.254/latest/meta-data")


def test_ollama_local_allowed():
    assert_ollama_is_local("http://localhost:11434")
    assert_ollama_is_local("http://127.0.0.1:11434")
