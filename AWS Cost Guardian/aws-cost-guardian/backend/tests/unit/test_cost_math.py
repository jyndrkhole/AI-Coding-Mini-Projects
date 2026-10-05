from decimal import Decimal

from app.core.money import month_over_month, recommendation_category


def test_month_over_month_for_the_demo_bill() -> None:
    change, percent = month_over_month(Decimal("18420"), Decimal("15870"))
    assert change == Decimal("2550.00")
    assert percent == Decimal("16.1")


def test_month_over_month_with_no_previous_spend() -> None:
    change, percent = month_over_month(Decimal("100"), Decimal("0"))
    assert change == Decimal("100.00")
    assert percent is None


def test_recommendation_groups() -> None:
    assert recommendation_category("SCHEDULE", "LOW") == "safe"
    assert recommendation_category("CLEANUP", "MEDIUM") == "review"
    assert recommendation_category("ARCHITECTURE", "MEDIUM") == "architecture"
    assert recommendation_category("ARCHITECTURE", "LOW") == "architecture"
