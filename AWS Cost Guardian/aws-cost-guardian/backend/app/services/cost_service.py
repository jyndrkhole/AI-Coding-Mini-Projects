"""Aggregate stored cost records. Totals are sums, not model estimates."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.aws.cost_explorer import PRIOR_MONTHS, _add_months
from app.core.config import get_settings
from app.core.exceptions import FinOpsError
from app.core.money import as_decimal, month_over_month
from app.db.models import CostRecord
from app.services.account_service import require_account
from app.services.pricing_service import PricingService


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise FinOpsError("Cost data unavailable.", status_code=503)


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _previous_month(month_start: date) -> date:
    return (month_start - timedelta(days=1)).replace(day=1)


def _period_label(month_start: date) -> str:
    return month_start.strftime("%B %Y")


# The chart tooltip lists the largest line movements. The rest are counted, not hidden by a percent rule.
MAX_CHART_COMPONENTS = 6
USAGE_TOTAL_TOLERANCE = Decimal("1.00")


def _current_month(session: Session, account_id: int) -> date:
    latest = (
        session.query(func.max(CostRecord.date))
        .filter(CostRecord.account_id == account_id, CostRecord.source == "daily")
        .scalar()
    )
    if latest is None:
        raise FinOpsError("Cost data unavailable.", status_code=503)
    return _as_date(latest).replace(day=1)


def _sum_source(session: Session, account_id: int, source: str, month_start: date):
    month_end = _next_month(month_start)
    total = (
        session.query(func.coalesce(func.sum(CostRecord.amount), 0))
        .filter(
            CostRecord.account_id == account_id,
            CostRecord.source == source,
            CostRecord.date >= month_start,
            CostRecord.date < month_end,
        )
        .scalar()
    )
    return as_decimal(total)


def _currency(session: Session, account_id: int) -> str:
    units = {
        row[0]
        for row in session.query(CostRecord.currency).filter(CostRecord.account_id == account_id).distinct().all()
        if row[0]
    }
    if not units:
        raise FinOpsError("Cost data unavailable.", status_code=503)
    if len(units) > 1:
        raise FinOpsError("Cost data uses more than one currency, so the totals were not combined.", status_code=409)
    return next(iter(units))


def _component_changes(earlier: dict, later: dict) -> tuple[list[dict], int]:
    changes = []
    for key in set(earlier) | set(later):
        delta = as_decimal(as_decimal(later.get(key, 0)) - as_decimal(earlier.get(key, 0)))
        if delta == 0:
            continue
        service, usage_type = key if isinstance(key, tuple) else (key, "")
        changes.append({"service": service, "usage_type": usage_type, "change": float(delta)})
    changes.sort(key=lambda item: abs(item["change"]), reverse=True)
    shown = changes[:MAX_CHART_COMPONENTS]
    return shown, len(changes) - len(shown)


def _history(session: Session, account_id: int, current: date) -> dict:
    start = _add_months(current, -PRIOR_MONTHS)
    services = {
        month: amounts
        for month, amounts in _keyed_month_amounts(session, account_id, "service", _service_key).items()
        if start <= month <= current
    }
    usage = _keyed_month_amounts(session, account_id, "usage", _usage_key)
    latest = _latest_daily(session, account_id)
    partial = latest < _next_month(current) - timedelta(days=1)
    months = []
    previous = None
    for month in sorted(services):
        point = {
            "month": month.strftime("%Y-%m"),
            "label": month.strftime("%b %Y"),
            "amount": float(_bucket_total(services[month])),
            "partial": partial and month == current,
            "compared_to": None,
            "change": None,
            "change_percent": None,
            "components": [],
            "other_component_count": 0,
        }
        if previous is not None and _next_month(previous) == month:
            earlier_total = _bucket_total(services[previous])
            later_total = _bucket_total(services[month])
            change, percent = month_over_month(later_total, earlier_total)
            earlier_usage = usage.get(previous, {})
            later_usage = usage.get(month, {})
            usage_matches = (
                abs(_bucket_total(earlier_usage) - earlier_total) <= USAGE_TOTAL_TOLERANCE
                and abs(_bucket_total(later_usage) - later_total) <= USAGE_TOTAL_TOLERANCE
                and (earlier_usage or later_usage)
            )
            components, others = _component_changes(
                earlier_usage if usage_matches else services[previous],
                later_usage if usage_matches else services[month],
            )
            point["compared_to"] = _period_label(previous)
            point["change"] = float(change)
            point["change_percent"] = None if percent is None else float(percent)
            point["components"] = components
            point["other_component_count"] = others
        months.append(point)
        previous = month
    prior_amounts = [as_decimal(point["amount"]) for point in months if not point["partial"] and point["month"] < current.strftime("%Y-%m")]
    average = None
    if prior_amounts:
        average = float(sum(prior_amounts, as_decimal(0)) / len(prior_amounts))
    if partial:
        note = (
            f"Current month is month-to-date through {latest.isoformat()}. "
            "Earlier months are full unblended Cost Explorer totals."
        )
    else:
        note = "Amounts are unblended Cost Explorer totals for each stored month."
    if len([point for point in months if not point["partial"]]) < PRIOR_MONTHS:
        note = f"{note} A refresh stores up to {PRIOR_MONTHS} earlier months."
    return {"history_note": note, "prior_months_average": average, "months": months}


def _keyed_month_amounts(session: Session, account_id: int, source: str, key_fn) -> dict[date, dict]:
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    grouped: dict[date, dict] = {}
    for row in rows:
        key = key_fn(row)
        if key is None:
            continue
        month = _as_date(row.date).replace(day=1)
        bucket = grouped.setdefault(month, {})
        bucket[key] = as_decimal(bucket.get(key, 0)) + as_decimal(row.amount)
    return grouped


def _bucket_total(bucket: dict | None) -> Decimal:
    if not bucket:
        return Decimal("0.00")
    return sum((as_decimal(amount) for amount in bucket.values()), Decimal("0.00"))


def _service_key(row: CostRecord) -> str | None:
    if row.service in {None, "", "all"}:
        return None
    return row.service


def _usage_key(row: CostRecord) -> tuple[str, str] | None:
    if row.service in {None, "", "all"} or not row.usage_type:
        return None
    return (row.service, row.usage_type)


def get_cost_summary(session: Session) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    previous = _previous_month(current)
    current_total = _sum_source(session, account.id, "service", current)
    previous_total = _sum_source(session, account.id, "service", previous)
    change, percent = month_over_month(current_total, previous_total)
    return {
        "currency": _currency(session, account.id),
        "current_period_label": _period_label(current),
        "previous_period_label": _period_label(previous),
        "current_monthly_cost": float(current_total),
        "previous_monthly_cost": float(previous_total),
        "mom_change_amount": float(change),
        "mom_change_percent": None if percent is None else float(percent),
        "mock_aws": get_settings().mock_aws,
        **_history(session, account.id, current),
    }


def get_daily_costs(session: Session) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    month_end = _next_month(current)
    rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == account.id,
            CostRecord.source == "daily",
            CostRecord.date >= current,
            CostRecord.date < month_end,
        )
        .order_by(CostRecord.date)
        .all()
    )
    return {
        "currency": _currency(session, account.id),
        "period_label": _period_label(current),
        "points": [
            {"date": _as_date(row.date).isoformat(), "amount": float(as_decimal(row.amount))} for row in rows
        ],
    }


def _pivot(session: Session, account_id: int, source: str, key_name: str, label_attr: str) -> list[dict]:
    current = _current_month(session, account_id)
    previous = _previous_month(current)
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        label = getattr(row, label_attr)
        bucket = grouped.setdefault(label, {"current": as_decimal(0), "previous": as_decimal(0)})
        month = _as_date(row.date).replace(day=1)
        amount = as_decimal(row.amount)
        if month == current:
            bucket["current"] = as_decimal(bucket["current"]) + amount
        elif month == previous:
            bucket["previous"] = as_decimal(bucket["previous"]) + amount
    items = []
    for label, bucket in grouped.items():
        current_amount = as_decimal(bucket["current"])
        previous_amount = as_decimal(bucket["previous"])
        change, percent = month_over_month(current_amount, previous_amount)
        items.append(
            {
                key_name: label,
                "current": float(current_amount),
                "previous": float(previous_amount),
                "change": float(change),
                "change_percent": None if percent is None else float(percent),
            }
        )
    items.sort(key=lambda item: item["current"], reverse=True)
    return items


def get_service_costs(session: Session) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    previous = _previous_month(current)
    return {
        "currency": _currency(session, account.id),
        "current_period_label": _period_label(current),
        "previous_period_label": _period_label(previous),
        "services": _pivot(session, account.id, "service", "service", "service"),
    }


def get_region_costs(session: Session) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    previous = _previous_month(current)
    return {
        "currency": _currency(session, account.id),
        "current_period_label": _period_label(current),
        "previous_period_label": _period_label(previous),
        "regions": _pivot(session, account.id, "region", "region", "region"),
    }


def _latest_daily(session: Session, account_id: int) -> date:
    latest = (
        session.query(func.max(CostRecord.date))
        .filter(CostRecord.account_id == account_id, CostRecord.source == "daily")
        .scalar()
    )
    if latest is None:
        raise FinOpsError("Cost data unavailable.", status_code=503)
    return _as_date(latest)


def _month_overlaps(month_start: date, start: date, end: date) -> bool:
    return month_start <= end and _next_month(month_start) > start


def _distinct_labels(session: Session, account_id: int, source: str, attribute: str) -> list[str]:
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    labels = {getattr(row, attribute) for row in rows if getattr(row, attribute) not in {None, "", "all"}}
    return sorted(labels)


def _comparison(
    session: Session,
    account_id: int,
    source: str,
    attribute: str,
    focus: date,
    previous: date,
    selected: str | None,
) -> list[dict]:
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        label = getattr(row, attribute)
        if label in {None, "", "all"}:
            continue
        if selected and label != selected:
            continue
        bucket = grouped.setdefault(label, {"current": as_decimal(0), "previous": as_decimal(0)})
        month = _as_date(row.date).replace(day=1)
        amount = as_decimal(row.amount)
        if month == focus:
            bucket["current"] = as_decimal(bucket["current"]) + amount
        elif month == previous:
            bucket["previous"] = as_decimal(bucket["previous"]) + amount
    items = []
    for label, bucket in grouped.items():
        current_amount = as_decimal(bucket["current"])
        previous_amount = as_decimal(bucket["previous"])
        change, percent = month_over_month(current_amount, previous_amount)
        items.append(
            {
                attribute: label,
                "current": float(current_amount),
                "previous": float(previous_amount),
                "change": float(change),
                "change_percent": None if percent is None else float(percent),
            }
        )
    items.sort(key=lambda item: item["current"], reverse=True)
    return items


def _usage_comparison(session: Session, account_id: int, focus: date, previous: date, service: str | None) -> list[dict]:
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == "usage")
        .all()
    )
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        if service and row.service != service:
            continue
        key = (row.service, row.usage_type)
        bucket = grouped.setdefault(key, {"current": as_decimal(0), "previous": as_decimal(0)})
        month = _as_date(row.date).replace(day=1)
        amount = as_decimal(row.amount)
        if month == focus:
            bucket["current"] = as_decimal(bucket["current"]) + amount
        elif month == previous:
            bucket["previous"] = as_decimal(bucket["previous"]) + amount
    pricing = PricingService()
    items = []
    for (row_service, usage_type), bucket in grouped.items():
        current_amount = as_decimal(bucket["current"])
        previous_amount = as_decimal(bucket["previous"])
        change, percent = month_over_month(current_amount, previous_amount)
        quote = pricing.quote(row_service, usage_type, "all")
        items.append(
            {
                "service": row_service,
                "usage_type": usage_type,
                "current": float(current_amount),
                "previous": float(previous_amount),
                "change": float(change),
                "change_percent": None if percent is None else float(percent),
                "pricing_available": quote["pricing_available"],
            }
        )
    items.sort(key=lambda item: item["current"], reverse=True)
    return items


def _monthly_series(
    session: Session,
    account_id: int,
    start: date,
    end: date,
    service: str | None,
    region: str | None,
) -> list[dict]:
    if service:
        source, attribute, selected = "service", "service", service
    elif region:
        source, attribute, selected = "region", "region", region
    else:
        source, attribute, selected = "service", "service", None
    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    totals: dict[date, object] = {}
    for row in rows:
        if selected and getattr(row, attribute) != selected:
            continue
        if getattr(row, attribute) in {None, "", "all"}:
            continue
        month = _as_date(row.date).replace(day=1)
        if not _month_overlaps(month, start, end):
            continue
        totals[month] = as_decimal(totals.get(month, 0)) + as_decimal(row.amount)
    return [
        {"month": month.strftime("%Y-%m"), "label": _period_label(month), "amount": float(as_decimal(amount))}
        for month, amount in sorted(totals.items())
    ]


def get_cost_explorer(
    session: Session,
    start: date | None,
    end: date | None,
    service: str | None,
    region: str | None,
) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    range_start = start or _previous_month(current)
    range_end = end or _latest_daily(session, account.id)
    if range_start > range_end:
        raise FinOpsError("Start date must be on or before the end date.", status_code=400)
    selected_service = service or None
    selected_region = region or None
    focus = range_end.replace(day=1)
    previous = _previous_month(focus)
    daily_rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == account.id,
            CostRecord.source == "daily",
            CostRecord.date >= range_start,
            CostRecord.date <= range_end,
        )
        .order_by(CostRecord.date)
        .all()
    )
    daily_note = None
    if selected_service or selected_region:
        daily_note = (
            "Daily cost is the account total. Service and region filters apply to their own "
            "breakdowns, which are collected separately."
        )
    settings = get_settings()
    return {
        "currency": _currency(session, account.id),
        "source_label": "Demo dataset" if settings.mock_aws else "Cost Explorer",
        "start": range_start.isoformat(),
        "end": range_end.isoformat(),
        "service": selected_service,
        "region": selected_region,
        "current_period_label": _period_label(focus),
        "previous_period_label": _period_label(previous),
        "available_services": _distinct_labels(session, account.id, "service", "service"),
        "available_regions": _distinct_labels(session, account.id, "region", "region"),
        "daily_note": daily_note,
        "monthly_note": (
            "Service, region, and usage amounts are full-month totals. A shorter date range "
            "filters the daily chart and does not prorate those months."
        ),
        "pricing_note": PricingService().quote("", "", "").get("reason"),
        "daily": [
            {"date": _as_date(row.date).isoformat(), "amount": float(as_decimal(row.amount))} for row in daily_rows
        ],
        "monthly": _monthly_series(session, account.id, range_start, range_end, selected_service, selected_region),
        "services": _comparison(session, account.id, "service", "service", focus, previous, selected_service),
        "regions": _comparison(session, account.id, "region", "region", focus, previous, selected_region),
        "usage_types": _usage_comparison(session, account.id, focus, previous, selected_service),
    }
