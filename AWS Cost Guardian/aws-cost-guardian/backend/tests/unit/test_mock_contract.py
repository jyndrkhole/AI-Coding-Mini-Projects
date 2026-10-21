import json
from decimal import Decimal
from pathlib import Path

MOCK_DATA = Path(__file__).resolve().parents[3] / "mock_data"
REQUIRED_FILES = (
    "costs/costs.json",
    "resources/ec2.json",
    "resources/ebs.json",
    "resources/rds.json",
    "resources/s3.json",
    "resources/lambda.json",
    "resources/nat.json",
    "metrics/metrics.json",
    "recommendations/demo.json",
    "recommendations/optimizer.json",
    "recommendations/cost_optimization_hub.json",
)


def _load(relative: str) -> dict:
    path = MOCK_DATA / relative
    assert path.is_file(), relative
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_required_mock_files_are_json() -> None:
    for relative in REQUIRED_FILES:
        _load(relative)


def test_demo_cost_totals_match_the_spec() -> None:
    costs = _load("costs/costs.json")
    current = costs["current_month"]
    previous = costs["previous_month"]
    daily = sum(Decimal(str(row["amount"])) for row in costs["daily"])
    services = sum(Decimal(str(row["amount"])) for row in costs["services"] if row["month"] == current)
    regions = sum(Decimal(str(row["amount"])) for row in costs["regions"] if row["month"] == current)
    previous_services = sum(Decimal(str(row["amount"])) for row in costs["services"] if row["month"] == previous)
    usage = sum(Decimal(str(row["amount"])) for row in costs["usage"] if row["month"] == current)
    previous_usage = sum(Decimal(str(row["amount"])) for row in costs["usage"] if row["month"] == previous)
    assert daily == services == regions == usage == Decimal("18420")
    assert previous_services == previous_usage == Decimal("15870")
    assert costs["forecast"]["month"] == current
    assert Decimal(str(costs["forecast"]["amount"])) == Decimal("18420")
    linked_current = sum(Decimal(str(row["amount"])) for row in costs["linked_accounts"] if row["month"] == current)
    linked_previous = sum(Decimal(str(row["amount"])) for row in costs["linked_accounts"] if row["month"] == previous)
    assert linked_current == Decimal("18420")
    assert linked_previous == Decimal("15870")
    assert costs["optimization_score"] == 68
    assert costs["account"]["aws_account_id"] == "123456789012"


def test_demo_savings_match_the_spec() -> None:
    payload = _load("recommendations/demo.json")
    monthly = sum(Decimal(str(row["estimated_monthly_savings"])) for row in payload["recommendations"])
    annual = sum(Decimal(str(row["estimated_annual_savings"])) for row in payload["recommendations"])
    assert monthly == Decimal("4250")
    assert annual == monthly * 12
    for row in payload["recommendations"]:
        assert row["evidence"]["pricing_available"] is False
        assert "guaranteed" not in json.dumps(row).lower()
