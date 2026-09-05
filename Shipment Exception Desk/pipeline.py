"""Core exercise: classify → compensate → escalate-or-resolve → draft."""

from chains import classify_chain, draft_email_chain, escalate_chain
from tools import (
    calculate_damage_compensation,
    calculate_delay_compensation,
    calculate_lost_compensation,
)

STANDARD_ESCALATION_THRESHOLD = 150.0
PREMIUM_ESCALATION_THRESHOLD = 75.0


def normalize_category(raw: str) -> str:
    """Map a model reply onto one of the four allowed categories."""
    if not raw:
        return "unknown"
    token = raw.strip().lower().split()[0]
    token = token.strip(".,:;!?`'\"")
    aliases = {
        "delay": "delayed",
        "delayed": "delayed",
        "damage": "damaged",
        "damaged": "damaged",
        "lost": "lost",
        "loss": "lost",
        "missing": "lost",
        "unknown": "unknown",
    }
    return aliases.get(token, "unknown")


def escalation_threshold(customer_tier: str) -> float:
    """Premium customers escalate at a lower dollar amount than standard ones."""
    tier = (customer_tier or "standard").strip().lower()
    if tier == "premium":
        return PREMIUM_ESCALATION_THRESHOLD
    return STANDARD_ESCALATION_THRESHOLD


def compensate(category: str, shipment_value: float) -> dict:
    if category == "delayed":
        return calculate_delay_compensation(shipment_value)
    if category == "damaged":
        return calculate_damage_compensation(shipment_value)
    if category == "lost":
        return calculate_lost_compensation(shipment_value)
    return {
        "category": "unknown",
        "amount": 0.0,
        "rate": 0.0,
        "policy": "No automatic payout until a human reviews the case.",
    }


def should_escalate(category: str, amount: float, customer_tier: str) -> tuple[bool, str]:
    if category == "unknown":
        return True, "Unclassifiable report — always escalate, regardless of value."
    threshold = escalation_threshold(customer_tier)
    if amount > threshold:
        return (
            True,
            f"Compensation ${amount:.2f} exceeds the {customer_tier} threshold of ${threshold:.2f}.",
        )
    return (
        False,
        f"Compensation ${amount:.2f} is at or under the {customer_tier} threshold of ${threshold:.2f}.",
    )


def process_exception(
    report: str,
    shipment_value: float,
    customer_tier: str = "standard",
) -> dict:
    """Run one exception all the way through classification, payout, and drafting."""
    steps: list[str] = []
    tier = (customer_tier or "standard").strip().lower()
    if tier not in {"standard", "premium"}:
        tier = "standard"

    raw_category = classify_chain.invoke({"report": report})
    category = normalize_category(raw_category)
    steps.append(f"Classified report as `{category}`.")

    compensation = compensate(category, shipment_value)
    amount = float(compensation["amount"])
    steps.append(
        f"Compensation: ${amount:.2f} — {compensation['policy']}"
    )

    escalated, reason = should_escalate(category, amount, tier)
    steps.append(reason)

    draft_inputs = {
        "report": report,
        "category": category,
        "customer_tier": tier,
        "shipment_value": f"{float(shipment_value):.2f}",
        "compensation_amount": f"{amount:.2f}",
        "escalation_reason": reason,
    }

    if escalated:
        message = escalate_chain.invoke(draft_inputs)
        outcome = "escalated"
        steps.append("Drafted an internal manager note.")
    else:
        message = draft_email_chain.invoke(draft_inputs)
        outcome = "auto-resolved"
        steps.append("Drafted a customer-facing resolution email.")

    return {
        "report": report,
        "shipment_value": float(shipment_value),
        "customer_tier": tier,
        "category": category,
        "compensation": compensation,
        "compensation_amount": amount,
        "escalated": escalated,
        "outcome": outcome,
        "escalation_reason": reason,
        "message": message.strip(),
        "steps": steps,
    }
