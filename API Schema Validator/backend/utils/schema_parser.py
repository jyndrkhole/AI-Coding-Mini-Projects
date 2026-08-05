"""Schema format detection and parsing utilities."""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

import yaml

from backend.models.schemas import SchemaFormat
from backend.utils.schema_sanitize import sanitize_schema_types


def detect_and_parse(content: str) -> Tuple[SchemaFormat, Dict[str, Any], str]:
    """
    Detect whether content is OpenAPI or JSON Schema and return
    (format, parsed_dict, normalized_json_text).
    """
    if not content or not content.strip():
        raise ValueError("Schema content is empty")

    data = _parse_yaml_or_json(content)
    if not isinstance(data, dict):
        raise ValueError("Schema root must be an object")

    data = sanitize_schema_types(data)
    fmt = _classify(data)
    normalized = json.dumps(data, indent=2, ensure_ascii=False)
    return fmt, data, normalized


def _parse_yaml_or_json(content: str) -> Any:
    text = content.strip()
    # Prefer JSON when it looks like JSON for clearer errors
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # Last resort: try JSON again for better message
        try:
            return json.loads(text)
        except json.JSONDecodeError as jexc:
            raise ValueError(f"Unable to parse as YAML or JSON: {exc}") from jexc


def _classify(data: Dict[str, Any]) -> SchemaFormat:
    if "openapi" in data or "swagger" in data:
        return SchemaFormat.OPENAPI
    if "$schema" in data or "properties" in data or "type" in data or "items" in data:
        return SchemaFormat.JSON_SCHEMA
    if "components" in data and "schemas" in data.get("components", {}):
        return SchemaFormat.OPENAPI
    return SchemaFormat.UNKNOWN


def parse_json_response(content: str) -> Any:
    """Parse and validate that response content is valid JSON."""
    if not content or not content.strip():
        raise ValueError("Response content is empty")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc


def estimate_line_number(json_text: str, json_path: str) -> int | None:
    """
    Best-effort line number for a JSON path by searching property keys.
    Returns 1-based line number or None.
    """
    if not json_path or json_path in ("$", ""):
        return 1

    # Extract last property segment that is a named key
    parts = [p for p in json_path.replace("[", ".").replace("]", "").split(".") if p and p != "$"]
    if not parts:
        return None

    key = parts[-1]
    if key.isdigit():
        # array index — search for previous named key if any
        named = [p for p in parts if not p.isdigit()]
        if not named:
            return None
        key = named[-1]

    needle = f'"{key}"'
    lines = json_text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if needle in line:
            return idx
    return None
