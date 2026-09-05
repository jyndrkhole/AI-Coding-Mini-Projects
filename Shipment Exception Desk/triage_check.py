"""Scripted check that exercises all four category / escalation branches."""

from pipeline import process_exception

CASES = [
    {
        "name": "mild delay — should auto-resolve",
        "report": (
            "Shipment NW-2201 was delivered two days late. The cartons are sealed "
            "and nothing is broken. Please credit us for the delay."
        ),
        "shipment_value": 80,
        "customer_tier": "standard",
        "expected_category": "delayed",
        "expected_escalated": False,
    },
    {
        "name": "high-value loss — should escalate",
        "report": (
            "The entire pallet for order NW-8809 is lost. Last scan was at the hub "
            "nine days ago and the carrier has closed it as lost in transit."
        ),
        "shipment_value": 400,
        "customer_tier": "standard",
        "expected_category": "lost",
        "expected_escalated": True,
    },
    {
        "name": "minor damage — should auto-resolve",
        "report": (
            "One corner of the box was crushed and two ceramic mugs arrived chipped. "
            "The rest of the order is usable. Filing a small damage claim."
        ),
        "shipment_value": 60,
        "customer_tier": "standard",
        "expected_category": "damaged",
        "expected_escalated": False,
    },
    {
        "name": "garbled report — must escalate regardless of value",
        "report": (
            "asdf qwerty ??? purple Tuesday invoice banana /////// "
            "pls fix thx 42%%% not sure what this is"
        ),
        "shipment_value": 25,
        "customer_tier": "standard",
        "expected_category": "unknown",
        "expected_escalated": True,
    },
]


def run_checks() -> int:
    failed = 0
    for case in CASES:
        print(f"\n=== {case['name']} ===")
        result = process_exception(
            case["report"],
            case["shipment_value"],
            case["customer_tier"],
        )
        category_ok = result["category"] == case["expected_category"]
        escalate_ok = result["escalated"] is case["expected_escalated"]
        print(f"category:  {result['category']} (expected {case['expected_category']})")
        print(
            f"escalated: {result['escalated']} (expected {case['expected_escalated']})"
        )
        print(f"amount:    ${result['compensation_amount']:.2f}")
        if category_ok and escalate_ok:
            print("PASS")
        else:
            print("FAIL")
            failed += 1

    print("\n" + "=" * 40)
    if failed:
        print(f"{failed} of {len(CASES)} checks failed.")
        return 1
    print(f"All {len(CASES)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
