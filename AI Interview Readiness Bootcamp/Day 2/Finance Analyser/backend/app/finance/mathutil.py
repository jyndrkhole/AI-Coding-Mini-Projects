"""Small numeric helpers shared by the statement parser and the ratio engine."""

from __future__ import annotations

import math
from typing import Any


def clean_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Return numerator / denominator, or None when the division is undefined."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def average(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left
    return (left + right) / 2


def pct_change(current: float | None, previous: float | None) -> float | None:
    """(current - previous) / |previous|. Absolute previous keeps a decline from a loss meaningful."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def cagr(start: float | None, end: float | None, periods: int) -> float | None:
    """(end / start) ** (1 / periods) - 1. Requires a positive start and at least one period."""
    if start is None or end is None or start <= 0 or end <= 0 or periods <= 0:
        return None
    return (end / start) ** (1 / periods) - 1
