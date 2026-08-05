"""Tests for date format handling and YAML date sanitization."""

from __future__ import annotations

import asyncio

import yaml

from backend.models.schemas import ValidationRequest
from backend.services.validation_service import ValidationService
from backend.utils.format_checkers import is_rfc_date
from backend.utils.schema_sanitize import sanitize_schema_types


def test_iso_date_strings_are_valid():
    assert is_rfc_date("2026-12-12")
    assert is_rfc_date(" 2026-12-12 ")
    assert is_rfc_date("2026-12-12T00:00:00Z")
    assert not is_rfc_date("2026-13-01")
    assert not is_rfc_date("12/12/2026")


def test_yaml_unquoted_dates_in_enum_do_not_break_string_instances():
    raw = """
type: object
required: [d]
properties:
  d:
    type: string
    format: date
    enum:
      - 2026-12-12
      - 2026-12-13
"""
    loaded = yaml.safe_load(raw)
    # Premature YAML date objects before sanitize
    assert hasattr(loaded["properties"]["d"]["enum"][0], "isoformat")
    cleaned = sanitize_schema_types(loaded)
    assert cleaned["properties"]["d"]["enum"] == ["2026-12-12", "2026-12-13"]


def test_validation_accepts_iso_date_for_format_date():
    schema = """
openapi: 3.0.3
info: {title: T, version: "1"}
paths:
  /x:
    get:
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                required: [d]
                properties:
                  d:
                    type: string
                    format: date
                    nullable: true
"""

    async def run():
        svc = ValidationService()
        return await svc.validate(
            ValidationRequest(
                schema_content=schema,
                response_content='{"d": "2026-12-12"}',
                path="/x",
                method="GET",
                status_code="200",
            )
        )

    result = asyncio.run(run())
    assert result.valid is True, [e.message for e in result.errors]


def test_yaml_enum_dates_with_string_response():
    schema = """
type: object
properties:
  d:
    type: string
    format: date
    enum:
      - 2026-12-12
"""

    async def run():
        svc = ValidationService()
        return await svc.validate(
            ValidationRequest(
                schema_content=schema,
                response_content='{"d": "2026-12-12"}',
            )
        )

    result = asyncio.run(run())
    assert result.valid is True, [e.message for e in result.errors]
