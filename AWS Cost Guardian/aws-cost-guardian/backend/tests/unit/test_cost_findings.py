from decimal import Decimal

from app.services.cost_findings import build_cost_findings


def test_architecture_findings_use_the_charge_as_an_upper_bound() -> None:
    findings = build_cost_findings(
        [
            ("EC2 - Other", "NatGateway-Hours", Decimal("194.40")),
            ("EC2", "BoxUsage:t3.large", Decimal("925.66")),
            ("EC2", "BoxUsage:t3.micro", Decimal("12.00")),
        ],
        "September 2026",
    )
    by_usage = {item["resource_id"]: item for item in findings}
    nat = by_usage["NatGateway-Hours"]
    assert nat["category"] == "architecture"
    assert nat["estimated_monthly_savings"] == 194.40
    assert nat["estimated_annual_savings"] == 2332.80
    assert "upper bound" in nat["assumptions"][0].lower()
    assert "guaranteed" in nat["assumptions"][0].lower()
    ec2 = by_usage["BoxUsage:t3.large"]
    assert ec2["category"] == "review"
    assert ec2["estimated_monthly_savings"] == 0
    assert "BoxUsage:t3.micro" not in by_usage
