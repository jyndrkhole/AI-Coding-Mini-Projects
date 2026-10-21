from datetime import date
from decimal import Decimal

import pytest

from app.aws.cost_explorer import CostExplorerReader, parse_cost_explorer_pages, parse_cost_forecast
from app.services.pricing_service import PricingService


def test_parser_reads_unblended_amounts_and_groups() -> None:
    pages = [
        {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-01", "End": "2026-10-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2", "BoxUsage:t3.micro"],
                            "Metrics": {"UnblendedCost": {"Amount": "25.50", "Unit": "USD"}},
                        }
                    ],
                }
            ]
        }
    ]
    lines = parse_cost_explorer_pages(pages, source="usage", group_by=["SERVICE", "USAGE_TYPE"])
    assert len(lines) == 1
    assert lines[0].service == "Amazon EC2"
    assert lines[0].usage_type == "BoxUsage:t3.micro"
    assert lines[0].amount == Decimal("25.50")
    assert lines[0].currency == "USD"


def test_parser_rejects_a_missing_amount() -> None:
    pages = [{"ResultsByTime": [{"TimePeriod": {"Start": "2026-09-01"}, "Total": {"UnblendedCost": {}}}]}]
    with pytest.raises(ValueError, match="UnblendedCost"):
        parse_cost_explorer_pages(pages, source="daily", group_by=[])


class _PagedCostExplorer:
    def __init__(self) -> None:
        self.calls = 0

    def get_cost_and_usage(self, **kwargs):
        self.calls += 1
        if kwargs.get("NextPageToken") == "page-2":
            return {
                "ResultsByTime": [
                    {
                        "TimePeriod": {"Start": "2026-09-02", "End": "2026-09-03"},
                        "Total": {"UnblendedCost": {"Amount": "4", "Unit": "USD"}},
                        "Groups": [],
                    }
                ]
            }
        return {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-01", "End": "2026-09-02"},
                    "Total": {"UnblendedCost": {"Amount": "3", "Unit": "USD"}},
                    "Groups": [],
                }
            ],
            "NextPageToken": "page-2",
        }


class _RecordingCostExplorer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get_cost_and_usage(self, **kwargs):
        self.calls.append(kwargs)
        return {"ResultsByTime": []}


def test_monthly_collection_covers_six_earlier_months() -> None:
    client = _RecordingCostExplorer()
    CostExplorerReader(client).collect(date(2026, 10, 5))
    monthly = [call for call in client.calls if call["Granularity"] == "MONTHLY"]
    daily = [call for call in client.calls if call["Granularity"] == "DAILY"]
    assert monthly[0]["TimePeriod"] == {"Start": "2026-04-01", "End": "2026-11-01"}
    assert daily[0]["TimePeriod"]["Start"] == "2026-09-01"


def test_reader_follows_the_next_page_token() -> None:
    reader = CostExplorerReader(_PagedCostExplorer())
    pages = reader.fetch_pages(date(2026, 9, 1), date(2026, 9, 3), "DAILY", [])
    assert len(pages) == 2
    lines = parse_cost_explorer_pages(pages, source="daily", group_by=[])
    assert [line.amount for line in lines] == [Decimal("3.00"), Decimal("4.00")]


class _RecordingForecast:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get_cost_forecast(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "Total": {"Amount": "40.10", "Unit": "USD"},
            "ForecastResultsByTime": [
                {
                    "MeanValue": "40.10",
                    "PredictionIntervalLowerBound": "30.00",
                    "PredictionIntervalUpperBound": "55.00",
                }
            ],
        }


def test_forecast_parser_reads_total_and_bounds() -> None:
    lines = parse_cost_forecast(
        {
            "Total": {"Amount": "40.10", "Unit": "USD"},
            "ForecastResultsByTime": [
                {
                    "MeanValue": "40.10",
                    "PredictionIntervalLowerBound": "30",
                    "PredictionIntervalUpperBound": "55",
                }
            ],
        },
        month_start=date(2026, 10, 1),
    )
    by_type = {line.usage_type: line for line in lines}
    assert by_type["mean"].amount == Decimal("40.10")
    assert by_type["lower"].amount == Decimal("30.00")
    assert by_type["upper"].amount == Decimal("55.00")
    assert by_type["mean"].source == "forecast"
    assert by_type["mean"].currency == "USD"


def test_parser_reads_linked_account_groups() -> None:
    pages = [
        {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-01", "End": "2026-10-01"},
                    "Groups": [
                        {"Keys": ["111122223333"], "Metrics": {"UnblendedCost": {"Amount": "9.00", "Unit": "USD"}}},
                    ],
                }
            ]
        }
    ]
    lines = parse_cost_explorer_pages(pages, source="account", group_by=["LINKED_ACCOUNT"])
    assert lines[0].service == "111122223333"
    assert lines[0].amount == Decimal("9.00")
    assert lines[0].source == "account"


def test_forecast_parser_returns_nothing_when_aws_omits_the_amount() -> None:
    assert parse_cost_forecast({"Total": {}}, month_start=date(2026, 10, 1)) == []


def test_forecast_collection_covers_the_rest_of_the_month() -> None:
    client = _RecordingForecast()
    lines = CostExplorerReader(client).collect_forecast(date(2026, 10, 21))
    assert client.calls == [
        {
            "TimePeriod": {"Start": "2026-10-21", "End": "2026-11-01"},
            "Granularity": "MONTHLY",
            "Metric": "UNBLENDED_COST",
            "PredictionIntervalLevel": 80,
        }
    ]
    assert [line.usage_type for line in lines] == ["mean", "lower", "upper"]
    assert lines[0].amount == Decimal("40.10")


def test_pricing_service_does_not_invent_a_rate() -> None:
    quote = PricingService().quote("EC2", "BoxUsage:t3.medium", "us-east-1")
    assert quote["pricing_available"] is False
    assert quote["amount"] is None
    assert "guaranteed" not in quote["reason"].lower()
