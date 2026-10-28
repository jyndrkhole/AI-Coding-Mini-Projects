"""Explicit risk flags. The published label is the count of these flags, not a model opinion."""

from __future__ import annotations

from app.domain.models import DCFResult, NewsResult, PeriodFinancials, RiskFlag, RiskResult, ValuationResult
from app.finance.mathutil import pct_change, safe_div
from app.finance.thresholds import CYCLICAL_INDUSTRY_KEYWORDS, FINANCIAL_INDUSTRY_KEYWORDS, RISK


def _flag(category: str, severity: str, title: str, evidence: str, impact: str) -> RiskFlag:
    return RiskFlag(category=category, severity=severity, title=title, evidence=evidence, impact=impact)  # type: ignore[arg-type]


def financial_and_business_flags(
    annual: list[PeriodFinancials],
    industry: str | None,
    sector: str | None,
) -> tuple[list[RiskFlag], int, list[str]]:
    flags: list[RiskFlag] = []
    evaluated = 0
    limitations: list[str] = []
    if not annual:
        return flags, 0, ["No annual statements were available for risk scoring."]
    latest = annual[-1]
    prior = annual[-2] if len(annual) > 1 else None
    text = f"{industry or ''} {sector or ''}".lower()
    financial_company = any(word in text for word in FINANCIAL_INDUSTRY_KEYWORDS)

    if latest.equity is None:
        limitations.append("Equity is unavailable.")
    else:
        evaluated += 1
        if latest.equity <= 0:
            flags.append(
                _flag(
                    "financial",
                    "high",
                    "Negative or zero equity",
                    f"Shareholders' equity is {latest.equity:,.0f}.",
                    "Leverage ratios and residual claims are impaired. This is not a low-debt signal.",
                )
            )

    if latest.total_debt is None or latest.equity is None or latest.equity <= 0:
        limitations.append("Debt-to-equity was not scored.")
    else:
        evaluated += 1
        ratio = latest.total_debt / latest.equity
        if ratio > RISK.debt_to_equity_high:
            flags.append(_flag("financial", "high", "High financial leverage", f"Debt to equity is {ratio:.2f}.", "Earnings shocks pass through to equity more quickly."))
        elif ratio > RISK.debt_to_equity_medium:
            flags.append(_flag("financial", "medium", "Elevated financial leverage", f"Debt to equity is {ratio:.2f}.", "Refinancing and rate changes matter more than at lower leverage."))

    if not financial_company and latest.current_assets is not None and latest.current_liabilities not in (None, 0):
        evaluated += 1
        current = latest.current_assets / latest.current_liabilities
        if current < RISK.current_ratio_high:
            flags.append(_flag("financial", "high", "Weak liquidity", f"Current ratio is {current:.2f}.", "Near-term obligations exceed current assets."))
        elif current < RISK.current_ratio_medium:
            flags.append(_flag("financial", "medium", "Tight liquidity", f"Current ratio is {current:.2f}.", "A working-capital squeeze would show up quickly."))
    elif financial_company:
        limitations.append("Current-ratio stress is not applied to banks and insurers.")

    if not financial_company and latest.total_debt not in (None, 0) and latest.interest_expense not in (None, 0) and latest.operating_income is not None:
        evaluated += 1
        coverage = latest.operating_income / latest.interest_expense
        if coverage < RISK.interest_coverage_high:
            flags.append(_flag("financial", "high", "Weak interest coverage", f"Operating income / interest expense is {coverage:.2f}.", "Operating profit may not cover the current interest bill."))
        elif coverage < RISK.interest_coverage_medium:
            flags.append(_flag("financial", "medium", "Modest interest coverage", f"Interest coverage is {coverage:.2f}.", "Higher borrowing costs would absorb a larger share of operating profit."))

    if latest.operating_cash_flow is not None:
        evaluated += 1
        if latest.operating_cash_flow < 0:
            flags.append(_flag("financial", "high", "Negative operating cash flow", f"Operating cash flow is {latest.operating_cash_flow:,.0f}.", "The business is consuming cash from operations."))

    fcf_values = [period.free_cash_flow for period in annual[-3:] if period.free_cash_flow is not None]
    if fcf_values:
        evaluated += 1
        if all(value < 0 for value in fcf_values):
            flags.append(_flag("financial", "high", "Persistent negative free cash flow", "Free cash flow is negative in every available recent year.", "A cash-flow valuation is weak, and funding depends on external capital or the balance sheet."))
        elif fcf_values[-1] < 0:
            flags.append(_flag("financial", "medium", "Latest free cash flow is negative", f"Latest free cash flow is {fcf_values[-1]:,.0f}.", "One weak year is not a trend, but it removes a clean DCF base."))

    if latest.net_income is not None and latest.net_income > 0 and latest.operating_cash_flow is not None:
        evaluated += 1
        if latest.operating_cash_flow < 0 or (safe_div(latest.operating_cash_flow, latest.net_income) or 0) < 0.5:
            flags.append(
                _flag(
                    "financial",
                    "medium",
                    "Earnings are poorly supported by cash",
                    f"Net income is {latest.net_income:,.0f} and operating cash flow is {latest.operating_cash_flow:,.0f}.",
                    "Reported profit may not be available for debt service, reinvestment, or dividends.",
                )
            )

    if prior and latest.revenue is not None and prior.revenue is not None:
        evaluated += 1
        growth = pct_change(latest.revenue, prior.revenue)
        if growth is not None and growth < 0:
            flags.append(_flag("financial", "medium", "Declining revenue", f"Revenue growth is {growth:.1%}.", "Operating leverage can turn a sales decline into a larger profit decline."))

    if prior and latest.revenue and prior.revenue and latest.operating_income is not None and prior.operating_income is not None:
        latest_margin = safe_div(latest.operating_income, latest.revenue)
        prior_margin = safe_div(prior.operating_income, prior.revenue)
        if latest_margin is not None and prior_margin is not None:
            evaluated += 1
            if prior_margin - latest_margin > RISK.margin_drop:
                flags.append(
                    _flag(
                        "financial",
                        "medium",
                        "Deteriorating operating margin",
                        f"Operating margin moved from {prior_margin:.1%} to {latest_margin:.1%}.",
                        "Less profit is retained from each unit of revenue.",
                    )
                )

    if industry or sector:
        evaluated += 1
        if any(word in text for word in CYCLICAL_INDUSTRY_KEYWORDS):
            flags.append(
                _flag(
                    "business",
                    "medium",
                    "Industry classified as cyclical",
                    f"Industry '{industry or sector}' matches the configured cyclical list.",
                    "Demand and margins can move with the cycle. This is a classification heuristic, not a measured customer exposure.",
                )
            )
    return flags, evaluated, limitations


def valuation_flags(valuation: ValuationResult) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    dcf: DCFResult = valuation.dcf
    if dcf.status == "unreliable":
        flags.append(
            _flag(
                "valuation",
                "medium",
                "Unreliable cash-flow valuation",
                "The DCF status is unreliable.",
                "The intrinsic-value point estimate has a wide error bar.",
            )
        )
    if dcf.terminal_value_share is not None and dcf.terminal_value_share > RISK.terminal_value_share:
        flags.append(
            _flag(
                "valuation",
                "medium",
                "Terminal value dominates",
                f"The discounted terminal value is {dcf.terminal_value_share:.0%} of the DCF total.",
                "Small changes in the discount rate or terminal growth move the value sharply.",
            )
        )
    if dcf.sensitivity and valuation.dcf.intrinsic_value_per_share:
        values = [cell.value_per_share for cell in dcf.sensitivity]
        base = valuation.dcf.intrinsic_value_per_share
        if base and (max(values) - min(values)) / abs(base) > RISK.sensitivity_range:
            flags.append(
                _flag(
                    "valuation",
                    "medium",
                    "High sensitivity to the discount rate",
                    "The sensitivity grid spans more than half of the base per-share value.",
                    "The valuation is an assumption range, not a single number.",
                )
            )
    if valuation.upside_percent is not None and valuation.upside_percent < RISK.premium_upside:
        flags.append(
            _flag(
                "valuation",
                "high",
                "Large premium to the calculated value",
                f"Estimated upside is {valuation.upside_percent:.1f}%.",
                "The market price embeds outcomes beyond the base assumptions.",
            )
        )
    return flags


def news_flags(news: NewsResult) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    legal = [article for article in news.articles if article.category == "legal" and article.sentiment in {"BEARISH", "STRONGLY_BEARISH"}]
    if legal:
        flags.append(
            _flag(
                "news",
                "medium",
                "Legal or regulatory headlines",
                legal[0].title,
                "The article is a headline, not a finding that a liability exists.",
            )
        )
    surprises = [
        article
        for article in news.articles
        if article.category == "earnings" and article.sentiment in {"BEARISH", "STRONGLY_BEARISH"}
    ]
    if surprises:
        flags.append(
            _flag(
                "news",
                "medium",
                "Negative earnings headline",
                surprises[0].title,
                "A headline can move the story before it changes the statements.",
            )
        )
    return flags


def classify_risk(flags: list[RiskFlag], evaluated: int, limitations: list[str]) -> RiskResult:
    if evaluated < RISK.min_evaluated:
        return RiskResult(
            label="INSUFFICIENT_DATA",
            flags=flags,
            evaluated_signals=evaluated,
            methodology=_methodology(),
            limitations=limitations + [f"Only {evaluated} risk signals could be evaluated. The minimum is {RISK.min_evaluated}."],
        )
    highs = sum(1 for flag in flags if flag.severity == "high")
    mediums = sum(1 for flag in flags if flag.severity == "medium")
    lows = sum(1 for flag in flags if flag.severity == "low")
    if highs >= 2:
        label = "HIGH"
    elif highs == 1 or mediums >= 3:
        label = "ELEVATED"
    elif mediums >= 1 or lows >= 3:
        label = "MODERATE"
    else:
        label = "LOW"
    return RiskResult(label=label, flags=flags, evaluated_signals=evaluated, methodology=_methodology(), limitations=limitations)


def _methodology() -> str:
    return (
        "Financial and business flags are counted from statement tests. "
        "Valuation flags are added only after a DCF or peer value exists. "
        "News flags require a retrieved article. "
        "Two or more high flags produce HIGH. One high flag, or three medium flags, produces ELEVATED. "
        "Any medium flag produces MODERATE. Otherwise the label is LOW. "
        "Fewer than three evaluated signals produces INSUFFICIENT_DATA."
    )
