"""Read unblended cost from Cost Explorer. Amounts are taken from the response, not priced locally."""

from datetime import date, timedelta

from app.core.money import as_decimal
from app.services.cost_store import CostLine


def _unblended(metrics: dict) -> tuple:
    try:
        cost = metrics["UnblendedCost"]
        amount = cost["Amount"]
        unit = cost["Unit"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Cost Explorer result is missing UnblendedCost amount or unit.") from exc
    if amount is None or unit is None or unit == "":
        raise ValueError("Cost Explorer result is missing UnblendedCost amount or unit.")
    return as_decimal(amount), str(unit)


def _dimensions(keys: list[str], group_by: list[str]) -> tuple[str, str, str]:
    mapped = {name: keys[index] for index, name in enumerate(group_by) if index < len(keys)}
    return mapped.get("SERVICE", "all"), mapped.get("REGION", "all"), mapped.get("USAGE_TYPE", "")


def parse_cost_forecast(payload: dict, *, month_start: date) -> list[CostLine]:
    total = payload.get("Total") or {}
    amount = total.get("Amount")
    unit = total.get("Unit")
    if amount is None or amount == "" or unit is None or unit == "":
        return []
    lines = [
        CostLine(month_start, "all", "all", "mean", as_decimal(amount), str(unit), "forecast"),
    ]
    results = payload.get("ForecastResultsByTime") or []
    if not results:
        return lines
    first = results[0]
    lower = first.get("PredictionIntervalLowerBound")
    upper = first.get("PredictionIntervalUpperBound")
    if lower not in (None, ""):
        lines.append(CostLine(month_start, "all", "all", "lower", as_decimal(lower), str(unit), "forecast"))
    if upper not in (None, ""):
        lines.append(CostLine(month_start, "all", "all", "upper", as_decimal(upper), str(unit), "forecast"))
    return lines


def parse_cost_explorer_pages(pages: list[dict], *, source: str, group_by: list[str]) -> list[CostLine]:
    lines: list[CostLine] = []
    for page in pages:
        for result in page.get("ResultsByTime", []):
            day = date.fromisoformat(result["TimePeriod"]["Start"])
            groups = result.get("Groups") or []
            if groups:
                for group in groups:
                    amount, unit = _unblended(group["Metrics"])
                    keys = group.get("Keys") or []
                    if group_by == ["LINKED_ACCOUNT"]:
                        account_id = keys[0] if keys else "all"
                        lines.append(CostLine(day, account_id, "all", "", amount, unit, source))
                    elif group_by == ["LINKED_ACCOUNT", "SERVICE"]:
                        mapped = {name: keys[index] for index, name in enumerate(group_by) if index < len(keys)}
                        lines.append(
                            CostLine(
                                day,
                                mapped.get("SERVICE", "all"),
                                "all",
                                mapped.get("LINKED_ACCOUNT", ""),
                                amount,
                                unit,
                                source,
                            )
                        )
                    else:
                        service, region, usage_type = _dimensions(keys, group_by)
                        lines.append(CostLine(day, service, region, usage_type, amount, unit, source))
            else:
                amount, unit = _unblended(result["Total"])
                lines.append(CostLine(day, "all", "all", "", amount, unit, source))
    return lines


PRIOR_MONTHS = 6


def _add_months(month_start: date, delta: int) -> date:
    index = month_start.year * 12 + month_start.month - 1 + delta
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


class CostExplorerReader:
    def __init__(self, client) -> None:
        self._client = client

    def collect(self, today: date) -> list[CostLine]:
        current_start = today.replace(day=1)
        previous_start = _add_months(current_start, -1)
        history_start = _add_months(current_start, -PRIOR_MONTHS)
        end_exclusive = today + timedelta(days=1)
        month_end = _add_months(current_start, 1)
        lines: list[CostLine] = []
        lines.extend(self._collect(previous_start, end_exclusive, "DAILY", [], "daily"))
        lines.extend(self._collect(previous_start, end_exclusive, "DAILY", ["SERVICE"], "daily_service"))
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["SERVICE"], "service"))
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["REGION"], "region"))
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["SERVICE", "USAGE_TYPE"], "usage"))
        account_lines = self._collect(history_start, month_end, "MONTHLY", ["LINKED_ACCOUNT"], "account")
        names = self._linked_account_names(history_start, month_end)
        if names:
            account_lines = [
                CostLine(
                    line.date,
                    line.service,
                    line.region,
                    names.get(line.service, line.usage_type),
                    line.amount,
                    line.currency,
                    line.source,
                )
                for line in account_lines
            ]
        lines.extend(account_lines)
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["LINKED_ACCOUNT", "SERVICE"], "account_service"))
        return lines

    def collect_forecast(self, today: date) -> list[CostLine]:
        # MONTHLY GetCostForecast still buckets the calendar month. Start must be
        # today; the Total is the month-end forecast, not remaining spend to add.
        month_start = today.replace(day=1)
        month_end = _add_months(month_start, 1)
        response = self._client.get_cost_forecast(
            TimePeriod={"Start": today.isoformat(), "End": month_end.isoformat()},
            Granularity="MONTHLY",
            Metric="UNBLENDED_COST",
            PredictionIntervalLevel=80,
        )
        return parse_cost_forecast(response, month_start=month_start)

    def fetch_pages(self, start: date, end: date, granularity: str, group_by: list[str]) -> list[dict]:
        pages: list[dict] = []
        token = None
        while True:
            params: dict = {
                "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
                "Granularity": granularity,
                "Metrics": ["UnblendedCost"],
            }
            if group_by:
                params["GroupBy"] = [{"Type": "DIMENSION", "Key": key} for key in group_by]
            if token:
                params["NextPageToken"] = token
            page = self._client.get_cost_and_usage(**params)
            pages.append(page)
            token = page.get("NextPageToken")
            if not token:
                return pages

    def _collect(self, start: date, end: date, granularity: str, group_by: list[str], source: str) -> list[CostLine]:
        pages = self.fetch_pages(start, end, granularity, group_by)
        return parse_cost_explorer_pages(pages, source=source, group_by=group_by)

    def _linked_account_names(self, start: date, end: date) -> dict[str, str]:
        getter = getattr(self._client, "get_dimension_values", None)
        if getter is None:
            return {}
        try:
            page = getter(
                TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                Dimension="LINKED_ACCOUNT",
            )
        except Exception:
            return {}
        names: dict[str, str] = {}
        for item in page.get("DimensionValues") or []:
            value = str(item.get("Value") or "")
            attrs = item.get("Attributes") or {}
            name = str(attrs.get("description") or attrs.get("linkedAccountName") or "").strip()
            if value and name:
                names[value] = name
        return names
