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


def parse_cost_explorer_pages(pages: list[dict], *, source: str, group_by: list[str]) -> list[CostLine]:
    lines: list[CostLine] = []
    for page in pages:
        for result in page.get("ResultsByTime", []):
            day = date.fromisoformat(result["TimePeriod"]["Start"])
            groups = result.get("Groups") or []
            if groups:
                for group in groups:
                    amount, unit = _unblended(group["Metrics"])
                    service, region, usage_type = _dimensions(group.get("Keys") or [], group_by)
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
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["SERVICE"], "service"))
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["REGION"], "region"))
        lines.extend(self._collect(history_start, month_end, "MONTHLY", ["SERVICE", "USAGE_TYPE"], "usage"))
        return lines

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
