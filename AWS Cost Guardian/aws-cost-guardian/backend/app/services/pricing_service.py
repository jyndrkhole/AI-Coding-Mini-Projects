"""Price quotes. This service does not invent a rate when it cannot price a usage type."""

from decimal import Decimal


class PricingService:
    def quote(self, service: str, usage_type: str, region: str) -> dict:
        del service, usage_type, region
        return {
            "pricing_available": False,
            "amount": None,
            "currency": None,
            "unit": None,
            "reason": (
                "A unit price was not calculated. Cost figures on this page are unblended "
                "Cost Explorer amounts, not a price-list estimate."
            ),
        }

    def unavailable_amount(self) -> Decimal | None:
        return None
