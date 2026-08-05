"""JSON path helpers and error classification."""

from __future__ import annotations

from typing import Any, List, Optional

from backend.models.schemas import ErrorCategory


def json_path_from_absolute(absolute_path: List[Any] | tuple) -> str:
    """Convert jsonschema absolute_path deque/list into a `$`.path form."""
    if not absolute_path:
        return "$"
    parts: List[str] = ["$"]
    for part in absolute_path:
        if isinstance(part, int):
            parts[-1] = f"{parts[-1]}[{part}]" if parts else f"$[{part}]"
        else:
            parts.append(str(part))
    return ".".join(parts) if len(parts) > 1 or parts[0] == "$" else "$"


def schema_path_from_relative(schema_path: List[Any] | tuple) -> str:
    if not schema_path:
        return "/"
    return "/" + "/".join(str(p) for p in schema_path)


def classify_validator(validator: Optional[str], message: str = "") -> ErrorCategory:
    """Map jsonschema validator names to UI error categories."""
    v = (validator or "").lower()
    msg = (message or "").lower()

    if v == "required" or "is a required property" in msg:
        return ErrorCategory.MISSING_FIELD
    if v == "type":
        return ErrorCategory.INVALID_TYPE
    if v == "enum":
        return ErrorCategory.ENUM_VIOLATION
    if v == "additionalproperties":
        return ErrorCategory.ADDITIONAL_PROPERTY
    if v in {"format", "pattern", "minlength", "maxlength", "minimum", "maximum", "exclusiveminimum", "exclusivemaximum"}:
        return ErrorCategory.INVALID_FORMAT
    if v == "oneof":
        return ErrorCategory.ONE_OF
    if v == "anyof":
        return ErrorCategory.ANY_OF
    if v == "allof":
        return ErrorCategory.ALL_OF
    return ErrorCategory.OTHER
