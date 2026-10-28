"""How complete the retrieved statements are. This is separate from the investment rating."""

from __future__ import annotations

from app.domain.models import CompanySnapshot, DataQuality

CORE_FIELDS = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "cash",
    "total_assets",
    "total_debt",
    "equity",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
)


def assess_quality(snapshot: CompanySnapshot) -> DataQuality:
    latest = snapshot.annual[-1] if snapshot.annual else None
    missing = list(snapshot.missing_fields)
    present = 0
    if latest is None:
        missing.append("annual statements")
    else:
        for field in CORE_FIELDS:
            if getattr(latest, field) is None:
                missing.append(field)
            else:
                present += 1
    if snapshot.market.price is None or snapshot.market.price <= 0:
        missing.append("market price")
    coverage = present / len(CORE_FIELDS)
    years = len(snapshot.annual)
    price_ok = snapshot.market.price is not None and snapshot.market.price > 0
    if latest is None or not price_ok:
        confidence = "INSUFFICIENT"
    elif years >= 4 and coverage >= 0.8:
        confidence = "HIGH"
    elif years >= 2 and coverage >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    limitations = list(snapshot.limitations)
    limitations.append("Market prices and statements are from Yahoo Finance through yfinance. They are not filings and can be restated, delayed, or incomplete.")
    if snapshot.market.currency is None:
        limitations.append("Currency was not reported. Per-share figures may be hard to compare with the quoted price.")
    return DataQuality(
        confidence=confidence,  # type: ignore[arg-type]
        years_annual=years,
        missing_fields=sorted(set(missing)),
        limitations=limitations,
        coverage_score=coverage,
    )
