"""API integration tests with FastAPI TestClient."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_validate_json_schema():
    schema = (SAMPLES / "schemas" / "user.jsonschema.json").read_text()
    response = (SAMPLES / "responses" / "user_invalid.json").read_text()
    resp = client.post(
        "/api/schema/validate",
        json={
            "schema_content": schema,
            "response_content": response,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["summary"]["total_errors"] >= 1


def test_load_schema_text():
    schema = (SAMPLES / "schemas" / "petstore.openapi.yaml").read_text()
    resp = client.post(
        "/api/schema/load",
        data={"source_type": "text", "content": schema},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["format"] == "openapi"
    assert len(body["endpoints"]) >= 1


def test_export_json():
    schema = (SAMPLES / "schemas" / "user.jsonschema.json").read_text()
    response = (SAMPLES / "responses" / "user_valid.json").read_text()
    validation = client.post(
        "/api/schema/validate",
        json={"schema_content": schema, "response_content": response},
    ).json()
    resp = client.post(
        "/api/schema/export",
        json={"format": "json", "validation_result": validation},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    payload = json.loads(resp.content)
    assert payload["valid"] is True
