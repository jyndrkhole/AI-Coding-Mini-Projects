from datetime import datetime, timezone
from pathlib import Path

import boto3
import pytest

from tests.conftest import build_client


def test_explorer_defaults_and_usage_match_the_bill(client) -> None:
    body = client.get("/api/costs/explorer").json()
    assert body["source_label"] == "Demo dataset"
    assert body["start"] == "2026-08-01"
    assert body["end"] == "2026-09-30"
    assert body["currency"] == "INR"
    assert sum(row["current"] for row in body["services"]) == 18420
    assert sum(row["previous"] for row in body["services"]) == 15870
    assert sum(row["current"] for row in body["usage_types"]) == 18420
    assert all(row["pricing_available"] is False for row in body["usage_types"])
    assert [point["month"] for point in body["monthly"]] == ["2026-08", "2026-09"]
    assert body["monthly"][1]["amount"] == 18420


def test_service_filter_and_partial_daily_range(client) -> None:
    filtered = client.get("/api/costs/explorer", params={"service": "EC2"}).json()
    assert [row["service"] for row in filtered["services"]] == ["EC2"]
    assert filtered["services"][0]["current"] == 7420
    assert filtered["services"][0]["previous"] == 6800
    assert filtered["services"][0]["change"] == 620
    assert filtered["services"][0]["change_percent"] == 9.1
    assert {row["service"] for row in filtered["usage_types"]} == {"EC2"}
    assert sum(row["current"] for row in filtered["usage_types"]) == 7420
    assert filtered["daily_note"] == "Daily cost is for the selected service."
    assert filtered["monthly"][1]["amount"] == 7420
    assert sum(point["amount"] for point in filtered["daily"]) != 18420
    accounts = {row["account_id"]: row for row in filtered["linked_accounts"]}
    assert accounts["123456789012"]["current"] == 4452
    assert accounts["111122223333"]["current"] == 2968

    daily = client.get(
        "/api/costs/explorer",
        params={"start": "2026-09-01", "end": "2026-09-15"},
    ).json()
    assert [point["date"] for point in daily["daily"]][0] == "2026-09-01"
    assert [point["date"] for point in daily["daily"]][-1] == "2026-09-15"
    assert len(daily["daily"]) == 15
    assert daily["services"][0]["service"] == "EC2"
    assert daily["services"][0]["current"] == 7420


def test_account_filter_limits_monthly_to_that_account(client) -> None:
    body = client.get("/api/costs/explorer", params={"linked_account": "111122223333"}).json()
    assert body["linked_account"] == "111122223333"
    assert body["monthly"][-1]["amount"] == 7368
    assert body["available_accounts"] == ["123456789012", "111122223333"]
    assert {row["account_id"] for row in body["linked_accounts"]} == {"123456789012", "111122223333"}


def test_region_filter(client) -> None:
    body = client.get("/api/costs/explorer", params={"region": "ap-south-1"}).json()
    assert [row["region"] for row in body["regions"]] == ["ap-south-1"]
    assert body["regions"][0]["current"] == 6280
    assert body["regions"][0]["previous"] == 4950
    assert body["monthly"][-1]["amount"] == 6280


def test_reversed_date_range_is_rejected(client) -> None:
    response = client.get("/api/costs/explorer", params={"start": "2026-09-20", "end": "2026-09-01"})
    assert response.status_code == 400
    assert "Start date" in response.json()["detail"]


def test_pricing_endpoint_declines_to_price(client) -> None:
    response = client.get(
        "/api/costs/pricing",
        params={"service": "EC2", "usage_type": "BoxUsage:t3.medium", "region": "us-east-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pricing_available"] is False
    assert body["amount"] is None


def test_mock_scan_does_not_call_aws(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_aws_call(*args, **kwargs):
        raise AssertionError("AWS was called")

    monkeypatch.setattr(boto3, "client", reject_aws_call)
    monkeypatch.setattr(boto3, "Session", reject_aws_call)
    response = client.post("/api/aws/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    steps = {step["service"]: step["status"] for step in body["steps"]}
    assert steps["cost_explorer"] == "ok"
    assert steps["sts"] == "skipped"
    assert steps["resources"] == "skipped"
    assert "No AWS calls" in next(step["detail"] for step in body["steps"] if step["service"] == "cost_explorer")
    assert client.get("/api/costs/summary").json()["current_monthly_cost"] == 18420


class _FakeSTS:
    def get_caller_identity(self):
        return {"Account": "999988887777", "Arn": "arn:aws:iam::999988887777:role/ReadOnly"}


class _FakeCostExplorer:
    def get_cost_forecast(self, **kwargs):
        assert kwargs["Granularity"] == "MONTHLY"
        assert kwargs["Metric"] == "UNBLENDED_COST"
        assert kwargs["PredictionIntervalLevel"] == 80
        return {
            "Total": {"Amount": "15.00", "Unit": "USD"},
            "ForecastResultsByTime": [
                {
                    "TimePeriod": kwargs["TimePeriod"],
                    "MeanValue": "15.00",
                    "PredictionIntervalLowerBound": "10.00",
                    "PredictionIntervalUpperBound": "22.00",
                }
            ],
        }

    def get_cost_and_usage(self, **kwargs):
        group_by = [item["Key"] for item in kwargs.get("GroupBy", [])]
        if kwargs["Granularity"] == "DAILY":
            if group_by == ["SERVICE"]:
                return {
                    "ResultsByTime": [
                        _grouped("2026-09-30", "2026-10-01", ["Amazon EC2"], "25.00"),
                    ]
                }
            return {
                "ResultsByTime": [
                    {
                        "TimePeriod": {"Start": "2026-09-30", "End": "2026-10-01"},
                        "Total": {"UnblendedCost": {"Amount": "25.00", "Unit": "USD"}},
                        "Groups": [],
                    }
                ]
            }
        if group_by == ["SERVICE"]:
            return {
                "ResultsByTime": [
                    _grouped("2026-08-01", "2026-09-01", ["Amazon EC2"], "10.00"),
                    _grouped("2026-09-01", "2026-10-01", ["Amazon EC2"], "25.00"),
                ]
            }
        if group_by == ["REGION"]:
            return {
                "ResultsByTime": [
                    _grouped("2026-08-01", "2026-09-01", ["us-east-1"], "10.00"),
                    _grouped("2026-09-01", "2026-10-01", ["us-east-1"], "25.00"),
                ]
            }
        if group_by == ["SERVICE", "USAGE_TYPE"]:
            return {
                "ResultsByTime": [
                    _grouped("2026-08-01", "2026-09-01", ["Amazon EC2", "BoxUsage:t3.micro"], "10.00"),
                    _grouped("2026-09-01", "2026-10-01", ["Amazon EC2", "BoxUsage:t3.micro"], "25.00"),
                ]
            }
        if group_by == ["LINKED_ACCOUNT"]:
            return {
                "ResultsByTime": [
                    _grouped("2026-08-01", "2026-09-01", ["999988887777"], "7.00"),
                    _grouped("2026-08-01", "2026-09-01", ["111122223333"], "3.00"),
                    _grouped("2026-09-01", "2026-10-01", ["999988887777"], "16.00"),
                    _grouped("2026-09-01", "2026-10-01", ["111122223333"], "9.00"),
                ]
            }
        if group_by == ["LINKED_ACCOUNT", "SERVICE"]:
            return {
                "ResultsByTime": [
                    _grouped("2026-08-01", "2026-09-01", ["999988887777", "Amazon EC2"], "7.00"),
                    _grouped("2026-08-01", "2026-09-01", ["111122223333", "Amazon EC2"], "3.00"),
                    _grouped("2026-09-01", "2026-10-01", ["999988887777", "Amazon EC2"], "16.00"),
                    _grouped("2026-09-01", "2026-10-01", ["111122223333", "Amazon EC2"], "9.00"),
                ]
            }
        raise AssertionError(group_by)


def _grouped(start: str, end: str, keys: list[str], amount: str) -> dict:
    return {
        "TimePeriod": {"Start": start, "End": end},
        "Groups": [{"Keys": keys, "Metrics": {"UnblendedCost": {"Amount": amount, "Unit": "USD"}}}],
    }


class _QuietAws:
    def __getattr__(self, name: str):
        def _empty(*args, **kwargs):
            return {}

        return _empty


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def test_real_scan_stores_cost_explorer_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.scan_service.datetime", _FrozenDateTime)
    monkeypatch.setattr(
        "app.services.scan_service.build_aws_clients",
        lambda: (_FakeSTS(), _FakeCostExplorer()),
    )
    monkeypatch.setattr(
        "app.services.scan_service.build_read_clients",
        lambda: {name: _QuietAws() for name in ("ec2", "rds", "s3", "lambda", "elbv2", "cloudwatch", "compute_optimizer", "cost_optimization_hub")},
    )
    test_client = build_client(monkeypatch, tmp_path / "real.db", "false")
    with test_client as client:
        scan = client.post("/api/aws/scan")
        summary = client.get("/api/costs/summary")
        account = client.get("/api/aws/account")
        explorer = client.get("/api/costs/explorer")
        filtered = client.get("/api/costs/explorer", params={"linked_account": "111122223333"})
        recommendations = client.get("/api/recommendations")
        savings = client.get("/api/savings")
        score = client.get("/api/optimization-score")
    assert scan.status_code == 200
    assert scan.json()["status"] == "completed"
    assert summary.json()["current_monthly_cost"] == 25
    assert summary.json()["forecasted_monthly_cost"] == 15
    assert summary.json()["forecast_available"] is True
    assert summary.json()["forecast_lower_bound"] == 10
    assert summary.json()["forecast_upper_bound"] == 22
    assert summary.json()["cost_scope_label"] == "Organization unblended cost"
    accounts = {row["account_id"]: row for row in summary.json()["linked_accounts"]}
    assert accounts["999988887777"]["current"] == 16
    assert accounts["999988887777"]["is_this_login"] is True
    assert accounts["111122223333"]["current"] == 9
    assert accounts["111122223333"]["is_this_login"] is False
    assert summary.json()["previous_monthly_cost"] == 10
    assert summary.json()["currency"] == "USD"
    assert next(step["status"] for step in scan.json()["steps"] if step["service"] == "cost_forecast") == "ok"
    assert summary.json()["mock_aws"] is False
    assert account.json()["aws_account_id"] == "999988887777"
    assert account.json()["mode"] == "aws"
    usage = explorer.json()["usage_types"][0]
    assert usage["usage_type"] == "BoxUsage:t3.micro"
    assert usage["pricing_available"] is False
    assert filtered.json()["linked_account"] == "111122223333"
    assert filtered.json()["services"][0]["current"] == 9
    assert filtered.json()["monthly"][-1]["amount"] == 9
    assert filtered.json()["usage_types"] == []
    assert recommendations.status_code == 200
    assert recommendations.json()["recommendations"] == []
    assert savings.status_code == 200
    assert savings.json()["potential_monthly_savings"] == 0
    assert savings.json()["label"] == "No recommendations collected yet."
    assert "AWS credentials unavailable" not in savings.text
    assert score.status_code == 200
    assert score.json()["score"] is None
    assert score.json()["source"] == "unavailable"

    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()


def test_cost_only_scan_skips_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_inventory(*args, **kwargs):
        raise AssertionError("Inventory was collected")

    monkeypatch.setattr("app.services.scan_service.datetime", _FrozenDateTime)
    monkeypatch.setattr(
        "app.services.scan_service.build_aws_clients",
        lambda: (_FakeSTS(), _FakeCostExplorer()),
    )
    monkeypatch.setattr("app.services.scan_service.build_read_clients", reject_inventory)
    test_client = build_client(monkeypatch, tmp_path / "cost-only.db", "false")
    with test_client as client:
        response = client.post("/api/aws/scan", params={"include_inventory": False})
        summary = client.get("/api/costs/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    steps = {step["service"]: step["status"] for step in body["steps"]}
    assert steps["cost_explorer"] == "ok"
    assert steps["cost_forecast"] == "ok"
    assert steps["resources"] == "skipped"
    assert steps["metrics"] == "skipped"
    assert steps["recommendations"] == "skipped"
    assert summary.json()["current_monthly_cost"] == 25

    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()


def test_cost_explorer_failure_does_not_fail_the_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Broken:
        def get_caller_identity(self):
            return {"Account": "999988887777", "Arn": "arn:aws:iam::999988887777:role/ReadOnly"}

        def get_cost_and_usage(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.services.scan_service.build_aws_clients", lambda: (Broken(), Broken()))
    test_client = build_client(monkeypatch, tmp_path / "broken.db", "false")
    with test_client as client:
        response = client.post("/api/aws/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed_with_errors"
    cost_step = next(step for step in body["steps"] if step["service"] == "cost_explorer")
    assert cost_step["error"] == "Cost Explorer unavailable."
    forecast_step = next(step for step in body["steps"] if step["service"] == "cost_forecast")
    assert forecast_step["status"] == "skipped"
    assert "Traceback" not in response.text
    assert "boom" not in response.text


class _UsageOnlyCostExplorer(_FakeCostExplorer):
    def get_cost_forecast(self, **kwargs):
        raise RuntimeError("forecast boom")


def test_forecast_failure_does_not_drop_usage_costs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.scan_service.datetime", _FrozenDateTime)
    monkeypatch.setattr(
        "app.services.scan_service.build_aws_clients",
        lambda: (_FakeSTS(), _UsageOnlyCostExplorer()),
    )
    monkeypatch.setattr(
        "app.services.scan_service.build_read_clients",
        lambda: {name: _QuietAws() for name in ("ec2", "rds", "s3", "lambda", "elbv2", "cloudwatch", "compute_optimizer", "cost_optimization_hub")},
    )
    test_client = build_client(monkeypatch, tmp_path / "forecast-broken.db", "false")
    with test_client as client:
        response = client.post("/api/aws/scan")
        summary = client.get("/api/costs/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed_with_errors"
    forecast_step = next(step for step in body["steps"] if step["service"] == "cost_forecast")
    assert forecast_step["error"] == "Cost forecast unavailable."
    assert "forecast boom" not in response.text
    assert summary.json()["current_monthly_cost"] == 25
    assert summary.json()["forecast_available"] is False
    assert summary.json()["forecasted_monthly_cost"] is None

    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()

    from app.core.config import get_settings
    from app.db.database import reset_engine

    reset_engine()
    get_settings.cache_clear()
