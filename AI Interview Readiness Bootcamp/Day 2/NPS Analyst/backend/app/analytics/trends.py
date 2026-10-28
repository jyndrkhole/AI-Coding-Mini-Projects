"""Monthly NPS and changes. Missing months are not invented."""

from __future__ import annotations

from app.analytics.nps import nps_by_month
from app.core.config import REFERENCE_NPS_CLAIMS
from app.data.normalizer import NormalizedResponse


def with_changes(responses: list[NormalizedResponse]) -> list[dict]:
    months = nps_by_month(responses)
    previous = None
    for row in months:
        if previous is None or row["nps"] is None or previous["nps"] is None:
            row["nps_change"] = None
            row["promoter_change"] = None
            row["passive_change"] = None
            row["detractor_change"] = None
        else:
            row["nps_change"] = row["nps"] - previous["nps"]
            row["promoter_change"] = row["promoters"] - previous["promoters"]
            row["passive_change"] = row["passives"] - previous["passives"]
            row["detractor_change"] = row["detractors"] - previous["detractors"]
        previous = row
    return months


def period_change(months: list[dict]) -> dict:
    if not months:
        return {"first_month": None, "last_month": None, "period_nps_change": None}
    first, last = months[0], months[-1]
    change = None
    if first.get("nps") is not None and last.get("nps") is not None and len(months) > 1:
        change = last["nps"] - first["nps"]
    return {
        "first_month": first["month"],
        "last_month": last["month"],
        "first_nps": first.get("nps"),
        "last_nps": last.get("nps"),
        "period_nps_change": change,
    }


def verify_reference_claims(months: list[dict]) -> list[dict]:
    """Compare the brief's named NPS figures with the calculation. The calculation is left unchanged."""
    by_month = {row["month"]: row.get("nps") for row in months}
    checks = []
    for month, claimed in REFERENCE_NPS_CLAIMS.items():
        actual = by_month.get(month)
        if month not in by_month:
            status = "month_not_in_dataset"
        elif actual is not None and abs(actual - claimed) < 1e-6:
            status = "match"
        else:
            status = "discrepancy"
        checks.append(
            {"month": month, "claimed_nps": claimed, "actual_nps": actual, "status": status}
        )
    return checks


def alert_for(months: list[dict], settings) -> dict:
    """Deterministic RED / AMBER / GREEN. The level does not depend on a model."""
    window = period_change(months)
    reasons: list[str] = []
    last_nps = window["last_nps"]
    change = window["period_nps_change"]
    level = "GREEN"
    if last_nps is not None and last_nps < settings.critical_nps:
        level = "RED"
        reasons.append(
            f"{window['last_month']} NPS is {last_nps:.1f}, below the critical threshold of {settings.critical_nps:.1f}."
        )
    if change is not None and -change >= settings.severe_decline_points:
        level = "RED"
        reasons.append(
            f"NPS fell by {-change:.1f} points from {window['first_month']} to {window['last_month']}, "
            f"reaching the severe-decline threshold of {settings.severe_decline_points:.1f} points."
        )
    if level != "RED" and change is not None and -change >= settings.mild_decline_points:
        level = "AMBER"
        reasons.append(
            f"NPS fell by {-change:.1f} points from {window['first_month']} to {window['last_month']}."
        )
    if level == "GREEN":
        reasons.append("No configured critical decline is present.")
    return {"level": level, "reasons": reasons, **window}
