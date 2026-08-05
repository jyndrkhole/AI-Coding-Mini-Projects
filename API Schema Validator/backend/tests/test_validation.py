"""Unit tests for the validation engine and OpenAPI extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from backend.models.schemas import ErrorCategory, ValidationRequest
from backend.services.validation_service import ValidationService
from backend.utils.schema_parser import detect_and_parse
from backend.validators.json_schema_validator import SchemaValidationEngine
from backend.validators.openapi_extractor import OpenAPIExtractor

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture
def engine() -> SchemaValidationEngine:
    return SchemaValidationEngine()


@pytest.fixture
def user_schema() -> dict:
    return json.loads((SAMPLES / "schemas" / "user.jsonschema.json").read_text())


@pytest.fixture
def petstore() -> dict:
    return yaml.safe_load((SAMPLES / "schemas" / "petstore.openapi.yaml").read_text())


def test_detect_json_schema(user_schema: dict):
    text = json.dumps(user_schema)
    fmt, data, _ = detect_and_parse(text)
    assert fmt.value == "json_schema"
    assert data["title"] == "User"


def test_detect_openapi(petstore: dict):
    text = yaml.dump(petstore)
    fmt, data, _ = detect_and_parse(text)
    assert fmt.value == "openapi"
    assert data["info"]["title"] == "Pet Store API"


def test_valid_user_passes(engine: SchemaValidationEngine, user_schema: dict):
    instance = json.loads((SAMPLES / "responses" / "user_valid.json").read_text())
    ok, errors, summary = engine.validate(user_schema, instance, response_text=json.dumps(instance, indent=2))
    assert ok is True
    assert summary.total_errors == 0
    assert errors == []


def test_invalid_user_reports_categories(engine: SchemaValidationEngine, user_schema: dict):
    text = (SAMPLES / "responses" / "user_invalid.json").read_text()
    instance = json.loads(text)
    ok, errors, summary = engine.validate(user_schema, instance, response_text=text)
    assert ok is False
    assert summary.total_errors > 0
    categories = {e.category for e in errors}
    assert ErrorCategory.INVALID_TYPE in categories or ErrorCategory.MISSING_FIELD in categories
    assert any(e.json_path.startswith("$") for e in errors)


def test_openapi_endpoint_listing(petstore: dict):
    extractor = OpenAPIExtractor()
    endpoints = extractor.list_endpoints(petstore)
    assert any(e.path == "/pets" and e.method == "GET" for e in endpoints)
    assert any(e.path == "/pets/{petId}" and e.method == "GET" for e in endpoints)


@pytest.mark.asyncio
async def test_validation_service_openapi_pet():
    service = ValidationService()
    schema = (SAMPLES / "schemas" / "petstore.openapi.yaml").read_text()
    response = (SAMPLES / "responses" / "pet_valid.json").read_text()
    result = await service.validate(
        ValidationRequest(
            schema_content=schema,
            response_content=response,
            path="/pets/{petId}",
            method="GET",
            status_code="200",
        )
    )
    assert result.valid is True


@pytest.mark.asyncio
async def test_validation_service_openapi_pet_invalid():
    service = ValidationService()
    schema = (SAMPLES / "schemas" / "petstore.openapi.yaml").read_text()
    response = (SAMPLES / "responses" / "pet_invalid.json").read_text()
    result = await service.validate(
        ValidationRequest(
            schema_content=schema,
            response_content=response,
            path="/pets/{petId}",
            method="GET",
            status_code="200",
        )
    )
    assert result.valid is False
    assert result.summary.total_errors >= 1
    cats = {e.category for e in result.errors}
    assert ErrorCategory.ENUM_VIOLATION in cats or ErrorCategory.INVALID_FORMAT in cats or ErrorCategory.ADDITIONAL_PROPERTY in cats
