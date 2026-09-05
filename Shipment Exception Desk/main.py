"""CLI runner — handy for quick terminal testing while you build."""

from pipeline import process_exception
from session import generate_daily_summary, record_exception

SAMPLES = [
    {
        "title": "Mild delay",
        "report": (
            "Order NW-1842 arrived two days after the promised date. "
            "The boxes are unopened and the goods look fine. Customer is annoyed."
        ),
        "shipment_value": 80,
        "customer_tier": "standard",
    },
    {
        "title": "High-value loss",
        "report": (
            "Tracking went dark a week ago. Carrier confirms the pallet is lost "
            "and will not be recovered. Customer needs a full replacement."
        ),
        "shipment_value": 400,
        "customer_tier": "standard",
    },
]


def print_result(title: str, result: dict) -> None:
    print("=" * 60)
    print(title)
    print(f"Category:     {result['category']}")
    print(f"Compensation: ${result['compensation_amount']:.2f}")
    print(f"Outcome:      {result['outcome']}")
    print("Steps:")
    for step in result["steps"]:
        print(f"  - {step}")
    print()
    print(result["message"])
    print()


if __name__ == "__main__":
    for sample in SAMPLES:
        result = process_exception(
            sample["report"],
            sample["shipment_value"],
            sample["customer_tier"],
        )
        record_exception(result)
        print_result(sample["title"], result)

    print("=" * 60)
    print(generate_daily_summary())
