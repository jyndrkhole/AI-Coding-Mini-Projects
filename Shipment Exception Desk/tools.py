"""Northwind compensation calculators.

Each function returns a dict (not a formatted string) so the pipeline can
use `amount` to decide whether to escalate.
"""

DELAY_RATE = 0.10
DAMAGE_RATE = 0.50
LOST_RATE = 1.00


def _money(value: float) -> float:
    return round(float(value), 2)


def calculate_delay_compensation(shipment_value: float) -> dict:
    """Goodwill credit: 10% of shipment value for a late-but-intact delivery."""
    amount = _money(shipment_value * DELAY_RATE)
    return {
        "category": "delayed",
        "amount": amount,
        "rate": DELAY_RATE,
        "policy": "Delay goodwill credit: 10% of shipment value.",
    }


def calculate_damage_compensation(shipment_value: float) -> dict:
    """Partial claim: 50% of shipment value for damaged goods."""
    amount = _money(shipment_value * DAMAGE_RATE)
    return {
        "category": "damaged",
        "amount": amount,
        "rate": DAMAGE_RATE,
        "policy": "Damage claim: 50% of shipment value.",
    }


def calculate_lost_compensation(shipment_value: float) -> dict:
    """Full replacement: 100% of shipment value when the shipment is lost."""
    amount = _money(shipment_value * LOST_RATE)
    return {
        "category": "lost",
        "amount": amount,
        "rate": LOST_RATE,
        "policy": "Lost shipment: 100% of shipment value.",
    }


if __name__ == "__main__":
    print("delay $80 ->", calculate_delay_compensation(80))
    print("damage $60 ->", calculate_damage_compensation(60))
    print("lost $400 ->", calculate_lost_compensation(400))
    assert calculate_delay_compensation(80)["amount"] == 8.0
    assert calculate_damage_compensation(60)["amount"] == 30.0
    assert calculate_lost_compensation(400)["amount"] == 400.0
    print("tools.py standalone checks passed.")
