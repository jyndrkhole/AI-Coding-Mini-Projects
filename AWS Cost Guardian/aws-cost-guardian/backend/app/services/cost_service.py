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


def _forecast_component(session: Session, account_id: int, month_start: date, usage_type: str):
    month_end = _next_month(month_start)
    rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == account_id,
            CostRecord.source == "forecast",
            CostRecord.usage_type == usage_type,
            CostRecord.date >= month_start,
            CostRecord.date < month_end,
        )
        .all()
    )
    if not rows:
        return None
    return sum((as_decimal(row.amount) for row in rows), Decimal("0.00"))


def _forecast_summary(session: Session, account_id: int, month_start: date) -> dict:
    forecast = _forecast_component(session, account_id, month_start, "mean")
    if forecast is None:
        return {
            "forecasted_monthly_cost": None,
            "forecast_available": False,
            "forecast_label": "Cost Explorer did not return a forecast for this month.",
            "forecast_lower_bound": None,
            "forecast_upper_bound": None,
        }
    lower = _forecast_component(session, account_id, month_start, "lower")
    upper = _forecast_component(session, account_id, month_start, "upper")
    return {
        "forecasted_monthly_cost": float(forecast),
        "forecast_available": True,
        "forecast_label": "Cost Explorer forecast for this month. Estimate, not a guaranteed bill.",
        "forecast_lower_bound": None if lower is None else float(lower),
        "forecast_upper_bound": None if upper is None else float(upper),
    }


def _linked_accounts(
    session: Session,
    guardian_id: int,
    login_account_id: str,
    focus: date,
    previous: date,
    selected_service: str | None = None,
) -> list[dict]:
    name_rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == guardian_id, CostRecord.source == "account")
        .all()
    )
    names: dict[str, str] = {}
    known: set[str] = set()
    for row in name_rows:
        acct = row.service
        if acct in {None, "", "all"}:
            continue
        known.add(acct)
        if row.usage_type:
            names[acct] = row.usage_type
    if selected_service:
        rows = (
            session.query(CostRecord)
            .filter(
                CostRecord.account_id == guardian_id,
                CostRecord.source == "account_service",
                CostRecord.service == selected_service,
            )
            .all()
        )
    else:
        rows = name_rows
    grouped: dict[str, dict[str, object]] = {
        acct: {"current": as_decimal(0), "previous": as_decimal(0)} for acct in known
    }
    for row in rows:
        acct = row.usage_type if selected_service else row.service
        if acct in {None, "", "all"}:
            continue
        if row.usage_type and not selected_service:
            names[acct] = row.usage_type
        bucket = grouped.setdefault(acct, {"current": as_decimal(0), "previous": as_decimal(0)})
        month = _as_date(row.date).replace(day=1)
        amount = as_decimal(row.amount)
        if month == focus:
            bucket["current"] = as_decimal(bucket["current"]) + amount
        elif month == previous:
            bucket["previous"] = as_decimal(bucket["previous"]) + amount
    items = []
    for acct, bucket in grouped.items():
        current_amount = as_decimal(bucket["current"])
        previous_amount = as_decimal(bucket["previous"])
        change, percent = month_over_month(current_amount, previous_amount)
        items.append(
            {
                "account_id": acct,
                "account_name": names.get(acct) or None,
                "is_this_login": acct == login_account_id,
                "current": float(current_amount),
                "previous": float(previous_amount),
                "change": float(change),
                "change_percent": None if percent is None else float(percent),
            }
        )
    items.sort(key=lambda item: (not item["is_this_login"], -item["current"]))
    return items


def _account_service_comparison(
    session: Session,
    guardian_id: int,
    focus: date,
    previous: date,
    linked_account: str,
    selected_service: str | None,
) -> list[dict]:
    rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == guardian_id,
            CostRecord.source == "account_service",
            CostRecord.usage_type == linked_account,
        )
        .all()
    )
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        label = row.service
        if label in {None, "", "all"}:
            continue
        if selected_service and label != selected_service:
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
                "service": label,
                "current": float(current_amount),
                "previous": float(previous_amount),
                "change": float(change),
                "change_percent": None if percent is None else float(percent),
            }
        )
    items.sort(key=lambda item: item["current"], reverse=True)
    return items


def get_cost_summary(session: Session) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    previous = _previous_month(current)
    current_total = _sum_source(session, account.id, "service", current)
    previous_total = _sum_source(session, account.id, "service", previous)
    change, percent = month_over_month(current_total, previous_total)
    linked = _linked_accounts(session, account.id, account.aws_account_id, current, previous)
    return {
        "currency": _currency(session, account.id),
        "current_period_label": _period_label(current),
        "previous_period_label": _period_label(previous),
        "current_monthly_cost": float(current_total),
        "previous_monthly_cost": float(previous_total),
        "mom_change_amount": float(change),
        "mom_change_percent": None if percent is None else float(percent),
        "cost_scope_label": "Organization unblended cost" if len(linked) > 1 else "Account unblended cost",
        "linked_accounts": linked,
        "mock_aws": get_settings().mock_aws,
        **_forecast_summary(session, account.id, current),
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
    linked_account: str | None = None,
) -> list[dict]:
    if linked_account and service:
        source = "account_service"

        def keep(row: CostRecord) -> bool:
            return row.usage_type == linked_account and row.service == service

    elif linked_account:
        source = "account"

        def keep(row: CostRecord) -> bool:
            return row.service == linked_account

    elif service:
        source = "service"

        def keep(row: CostRecord) -> bool:
            return row.service == service and row.service not in {None, "", "all"}

    elif region:
        source = "region"

        def keep(row: CostRecord) -> bool:
            return row.region == region and row.region not in {None, "", "all"}

    else:
        source = "service"

        def keep(row: CostRecord) -> bool:
            return row.service not in {None, "", "all"}

    rows = (
        session.query(CostRecord)
        .filter(CostRecord.account_id == account_id, CostRecord.source == source)
        .all()
    )
    totals: dict[date, object] = {}
    for row in rows:
        if not keep(row):
            continue
        month = _as_date(row.date).replace(day=1)
        if not _month_overlaps(month, start, end):
            continue
        totals[month] = as_decimal(totals.get(month, 0)) + as_decimal(row.amount)
    return [
        {"month": month.strftime("%Y-%m"), "label": _period_label(month), "amount": float(as_decimal(amount))}
        for month, amount in sorted(totals.items())
    ]


def _daily_rows(
    session: Session,
    account_id: int,
    range_start: date,
    range_end: date,
    selected_service: str | None,
) -> tuple[list, bool]:
    if selected_service:
        rows = (
            session.query(CostRecord)
            .filter(
                CostRecord.account_id == account_id,
                CostRecord.source == "daily_service",
                CostRecord.service == selected_service,
                CostRecord.date >= range_start,
                CostRecord.date <= range_end,
            )
            .order_by(CostRecord.date)
            .all()
        )
        if rows:
            return rows, True
        return [], False
    rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == account_id,
            CostRecord.source == "daily",
            CostRecord.date >= range_start,
            CostRecord.date <= range_end,
        )
        .order_by(CostRecord.date)
        .all()
    )
    return rows, False


def get_cost_explorer(
    session: Session,
    start: date | None,
    end: date | None,
    service: str | None,
    region: str | None,
    linked_account: str | None = None,
) -> dict:
    account = require_account(session)
    current = _current_month(session, account.id)
    range_start = start or _previous_month(current)
    range_end = end or _latest_daily(session, account.id)
    if range_start > range_end:
        raise FinOpsError("Start date must be on or before the end date.", status_code=400)
    selected_service = service or None
    selected_region = region or None
    selected_account = linked_account or None
    focus = range_end.replace(day=1)
    previous = _previous_month(focus)
    daily_rows, daily_filtered = _daily_rows(
        session, account.id, range_start, range_end, selected_service
    )
    linked_all = _linked_accounts(session, account.id, account.aws_account_id, focus, previous)
    linked = _linked_accounts(
        session, account.id, account.aws_account_id, focus, previous, selected_service
    )
    daily_note = None
    if selected_service and daily_filtered:
        daily_note = "Daily cost is for the selected service."
    elif selected_service:
        daily_note = (
            "Daily cost by service is not stored yet. Click Refresh costs, then filter again. "
            "Chargeback and service amounts below are already for this service."
        )
    elif selected_region:
        daily_note = (
            "Daily cost is the organization total. The region filter applies to regional distribution "
            "and monthly cost."
        )
    if selected_account:
        extra = (
            "Chargeback, monthly cost, and service amounts are for the selected account. "
            "Daily cost stays organization-wide unless a service is also selected."
        )
        daily_note = f"{daily_note} {extra}".strip() if daily_note else extra
        services = _account_service_comparison(
            session, account.id, focus, previous, selected_account, selected_service
        )
        usage_types: list[dict] = []
    else:
        services = _comparison(session, account.id, "service", "service", focus, previous, selected_service)
        usage_types = _usage_comparison(session, account.id, focus, previous, selected_service)
    settings = get_settings()
    account_note = None
    if len(linked) > 1:
        account_note = (
            "AWS invoices the management account for the full organization total. "
            "Charge each linked account its own row. The row marked This account is usage "
            "in the login you connected; that part is typically yours unless you allocate it."
        )
    return {
        "currency": _currency(session, account.id),
        "source_label": "Demo dataset" if settings.mock_aws else "Cost Explorer",
        "start": range_start.isoformat(),
        "end": range_end.isoformat(),
        "service": selected_service,
        "region": selected_region,
        "linked_account": selected_account,
        "current_period_label": _period_label(focus),
        "previous_period_label": _period_label(previous),
        "available_services": _distinct_labels(session, account.id, "service", "service"),
        "available_regions": _distinct_labels(session, account.id, "region", "region"),
        "available_accounts": [item["account_id"] for item in linked_all],
        "daily_note": daily_note,
        "monthly_note": (
            "Service, region, and usage amounts are full-month totals. A shorter date range "
            "filters the daily chart and does not prorate those months."
        ),
        "account_note": account_note,
        "pricing_note": PricingService().quote("", "", "").get("reason"),
        "daily": [
            {"date": _as_date(row.date).isoformat(), "amount": float(as_decimal(row.amount))} for row in daily_rows
        ],
        "monthly": _monthly_series(
            session, account.id, range_start, range_end, selected_service, selected_region, selected_account
        ),
        "services": services,
        "regions": _comparison(session, account.id, "region", "region", focus, previous, selected_region),
        "usage_types": usage_types,
        "linked_accounts": linked,
    }
