from pathlib import Path

import boto3
import pytest

from tests.conftest import build_client


def test_health_reports_mock_mode_and_database(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "aws-cost-guardian"
    assert body["mock_aws"] is True
    assert body["database"] == "ok"
    assert "traceback" not in response.text.lower()


def test_demo_account_identity(client) -> None:
    response = client.get("/api/aws/account")
    assert response.status_code == 200
    body = response.json()
    assert body["aws_account_id"] == "123456789012"
    assert body["account_alias"] == "demo-finops"
    assert body["region"] == "us-east-1"
    assert body["authenticated_role"].endswith("AWSCostGuardianReadOnly")
    assert body["mock_aws"] is True
    assert body["mode"] == "demo"
    assert body["last_scan_at"].startswith("2026-10-04T08:30:00")


def test_cost_summary_uses_stored_totals(client) -> None:
    body = client.get("/api/costs/summary").json()
    assert body["current_monthly_cost"] == 18420
    assert body["previous_monthly_cost"] == 15870
    assert body["mom_change_amount"] == 2550
    assert body["mom_change_percent"] == 16.1
    assert body["current_period_label"] == "September 2026"
    assert body["previous_period_label"] == "August 2026"
    assert body["currency"] == "INR"
    assert [point["month"] for point in body["months"]] == ["2026-08", "2026-09"]
    assert body["months"][1]["partial"] is False
    assert body["prior_months_average"] == 15870
    assert body["months"][0]["compared_to"] is None
    assert body["months"][0]["components"] == []
    september = body["months"][1]
    assert september["compared_to"] == "August 2026"
    assert september["change"] == 2550
    assert september["change_percent"] == 16.1
    components = [(item["service"], item["usage_type"], item["change"]) for item in september["components"]]
    assert components[0] == ("Data Transfer", "DataTransfer-Out-Bytes", 860)
    assert ("EC2", "BoxUsage:t3.medium", 400) in components
    assert ("NAT Gateway", "NatGateway-Bytes", 480) in components
    assert september["other_component_count"] >= 1


def test_daily_service_and_region_totals_agree(client) -> None:
    daily = client.get("/api/costs/daily").json()
    services = client.get("/api/costs/services").json()
    regions = client.get("/api/costs/regions").json()
    assert len(daily["points"]) == 30
    assert sum(point["amount"] for point in daily["points"]) == 18420
    assert sum(item["current"] for item in services["services"]) == 18420
    assert sum(item["previous"] for item in services["services"]) == 15870
    assert sum(item["current"] for item in regions["regions"]) == 18420
    assert services["services"][0]["service"] == "EC2"


def test_savings_and_score(client) -> None:
    savings = client.get("/api/savings").json()
    score = client.get("/api/optimization-score").json()
    assert savings["label"] == "Estimated potential savings"
    assert savings["potential_monthly_savings"] == 4250
    assert savings["potential_annual_savings"] == 51000
    assert savings["safe_monthly_savings"] == 1780
    assert savings["review_monthly_savings"] == 1470
    assert savings["architecture_monthly_savings"] == 1000
    assert score["score"] == 68
    assert score["source"] == "demo_dataset"


def test_recommendations_are_grouped_and_do_not_guarantee_savings(client) -> None:
    body = client.get("/api/recommendations").json()
    rows = body["recommendations"]
    assert len(rows) == 6
    grouped = {"safe": 0, "review": 0, "architecture": 0}
    for row in rows:
        grouped[row["category"]] += row["estimated_monthly_savings"]
    assert grouped == {"safe": 1780, "review": 1470, "architecture": 1000}
    text = client.get("/api/recommendations").text.lower()
    assert "guaranteed" not in text
    prod = next(row for row in rows if row["resource_id"] == "i-0prodapp001")
    assert "mysql" in prod["evidence_summary"].lower()
    assert prod["category"] == "review"


def test_mock_mode_does_not_call_aws(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_aws_call(*args, **kwargs):
        raise AssertionError("AWS was called")

    monkeypatch.setattr(boto3, "client", reject_aws_call)
    monkeypatch.setattr(boto3, "Session", reject_aws_call)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/costs/summary").status_code == 200
    assert client.get("/api/aws/account").status_code == 200


def test_mock_resources_and_metrics_are_seeded(client) -> None:
    from app.db.database import get_sessionmaker
    from app.db.models import Metric, Resource

    session = get_sessionmaker()()
    try:
        assert session.query(Resource).count() == 17
        assert session.query(Metric).count() == 5
        prod = session.query(Resource).filter_by(resource_id="i-0prodapp001").one()
        assert "mysql" in prod.metadata_json["roles"]
    finally:
        session.close()


def test_disabled_mock_mode_does_not_invent_costs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_client = build_client(monkeypatch, tmp_path / "empty.db", "false")
    with test_client as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["mock_aws"] is False
        costs = client.get("/api/costs/summary")
        account = client.get("/api/aws/account")
    assert costs.status_code == 503
    assert account.status_code == 503
    assert "AWS credentials unavailable" in costs.json()["detail"]
    assert "AWS credentials unavailable" in account.json()["detail"]

    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()
