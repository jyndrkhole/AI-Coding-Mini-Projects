"""Normalize schemas loaded from YAML/OpenAPI for JSON Schema validators."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Set, Union


def sanitize_schema_types(node: Any, *, _seen: Set[int] | None = None) -> Any:
    """
    Recursively convert YAML-native date/time objects to ISO strings and
    adapt OpenAPI-only constructs to JSON Schema-friendly forms.

    Why: PyYAML parses unquoted `2026-12-12` as datetime.date. If that lands
    in `enum` / `const` / `default`, string API responses like \"2026-12-12\"
    incorrectly fail validation.
    """
    if _seen is None:
        _seen = set()

    if isinstance(node, dict):
        obj_id = id(node)
        if obj_id in _seen:
            return node
        _seen.add(obj_id)

        out: Dict[str, Any] = {}
        for key, value in node.items():
            out[key] = sanitize_schema_types(value, _seen=_seen)

        # OpenAPI nullable → JSON Schema type union (only when type is present)
        if out.get("nullable") is True:
            out.pop("nullable", None)
            if "type" in out:
                out["type"] = _union_with_null(out.get("type"))

        return out

    if isinstance(node, list):
        return [sanitize_schema_types(item, _seen=_seen) for item in node]

    return _scalar_to_jsonable(node)


def _scalar_to_jsonable(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        # Prefer date-only when time is midnight and tz-naive (YAML date→datetime occasional)
        if (
            value.hour == 0
            and value.minute == 0
            and value.second == 0
            and value.microsecond == 0
            and value.tzinfo is None
        ):
            return value.date().isoformat()
        return value.isoformat()
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.time):
        return value.isoformat()
    return value


def _union_with_null(existing: Any) -> Union[str, List[Any]]:
    if existing is None:
        return "null"
    if isinstance(existing, list):
        types = list(existing)
        if "null" not in types:
            types.append("null")
        return types
    if existing == "null":
        return "null"
    return [existing, "null"]
