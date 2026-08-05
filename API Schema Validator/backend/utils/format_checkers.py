"""Format checkers that behave well for real-world API date/time strings."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from jsonschema import FormatChecker

# RFC 3339 full-date
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
# Allow optional time portion; we only validate the date segment for format=date
_DATE_PREFIX_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[Tt ].*)?$")


def _as_trimmed_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return None


def is_rfc_date(value: Any) -> bool:
    """
    True for ISO calendar dates like 2026-12-12.

    Also accepts datetime.date instances and (leniently) ISO date-time values
    when only the date portion is required by format: date — common in APIs.
    """
    text = _as_trimmed_str(value)
    if text is None:
        return True  # let `type` keyword handle non-strings

    match = _DATE_PREFIX_RE.match(text)
    if not match:
        return False
    try:
        dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return True
    except ValueError:
        return False


def is_rfc_date_time(value: Any) -> bool:
    text = _as_trimmed_str(value)
    if text is None:
        return True
    # fromisoformat doesn't accept trailing Z in older Python — normalize
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt.datetime.fromisoformat(normalized)
        return True
    except ValueError:
        # Fall back: date-only is acceptable for many APIs declaring date-time loosely
        return bool(_DATE_RE.match(text)) and is_rfc_date(text)


def build_format_checker() -> FormatChecker:
    checker = FormatChecker()
    # Override stock checkers — stock date rejects nothing weird except we need
    # trim + YAML date objects + optional time suffix for format=date.
    checker.checks("date", raises=(ValueError, TypeError))(is_rfc_date)
    checker.checks("date-time", raises=(ValueError, TypeError))(is_rfc_date_time)
    return checker
