"""Deterministic money helpers. These never estimate a price."""

from decimal import ROUND_HALF_UP, Decimal

TWOPLACES = Decimal("0.01")
ONEPLACE = Decimal("0.1")


def as_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def month_over_month(current: Decimal, previous: Decimal) -> tuple[Decimal, Decimal | None]:
    change = (current - previous).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if previous == 0:
        return change, None
    percent = (change / previous * Decimal("100")).quantize(ONEPLACE, rounding=ROUND_HALF_UP)
    return change, percent


def recommendation_category(action_type: str, risk_level: str) -> str:
    if action_type == "ARCHITECTURE":
        return "architecture"
    if risk_level == "LOW":
        return "safe"
    return "review"
