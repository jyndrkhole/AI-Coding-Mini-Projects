"""Rule-based financial health. The language model is not allowed to choose this label."""

from __future__ import annotations

from app.domain.models import HealthResult, Metric, PeriodFinancials
from app.finance.ratios import build_metrics, history_points
from app.finance.thresholds import FINANCIAL_INDUSTRY_KEYWORDS, HEALTH


def _is_financial_company(industry: str | None, sector: str | None) -> bool:
    text = f"{industry or ''} {sector or ''}".lower()
    return any(word in text for word in FINANCIAL_INDUSTRY_KEYWORDS)


def _by_key(metrics: list[Metric]) -> dict[str, Metric]:
    return {metric.key: metric for metric in metrics}


def classify_health(
    annual: list[PeriodFinancials],
    industry: str | None = None,
    sector: str | None = None,
) -> HealthResult:
    metrics = build_metrics(annual)
    found = _by_key(metrics)
    financial = _is_financial_company(industry, sector)
    latest = annual[-1] if annual else None
    checks: list[tuple[str, bool | None, str]] = []

    def add(name: str, passed: bool | None, evidence: str) -> None:
        checks.append((name, passed, evidence))

    growth = found.get("revenue_growth")
    if growth and growth.value is not None:
        add("Revenue is growing", growth.value > 0, f"Latest revenue growth is {growth.value:.1%}.")
    else:
        add("Revenue is growing", None, "Revenue growth cannot be calculated.")

    operating = found.get("operating_margin")
    if operating and operating.value is not None:
        add(
            "Operating margin clears the heuristic",
            operating.value >= HEALTH.operating_margin,
            f"Operating margin is {operating.value:.1%}. Threshold is {HEALTH.operating_margin:.0%}.",
        )
    else:
        add("Operating margin clears the heuristic", None, "Operating margin is unavailable.")

    net = found.get("net_margin")
    if net and net.value is not None:
        add(
            "Net margin is positive and adequate",
            net.value >= HEALTH.net_margin,
            f"Net margin is {net.value:.1%}. Threshold is {HEALTH.net_margin:.0%}.",
        )
    else:
        add("Net margin is positive and adequate", None, "Net margin is unavailable.")

    roe = found.get("roe")
    if latest and latest.equity is not None and latest.equity <= 0:
        add("Equity is positive", False, "Shareholders' equity is negative. ROE is not used as a strength.")
    elif roe and roe.value is not None and roe.interpretable:
        add("Return on equity clears the heuristic", roe.value >= HEALTH.roe, f"ROE is {roe.value:.1%}.")
    else:
        add("Return on equity clears the heuristic", None, "ROE is unavailable.")

    if not financial:
        current = found.get("current_ratio")
        if current and current.value is not None:
            add(
                "Liquidity covers near-term liabilities",
                current.value >= HEALTH.current_ratio,
                f"Current ratio is {current.value:.2f}. Threshold is {HEALTH.current_ratio:.2f}.",
            )
        else:
            add("Liquidity covers near-term liabilities", None, "Current ratio is unavailable.")
    else:
        add("Liquidity covers near-term liabilities", None, "Current ratio is not applied to banks and insurers.")

    de = found.get("debt_to_equity")
    if latest and latest.equity is not None and latest.equity <= 0:
        add("Leverage is within the heuristic", False, "Negative equity. Debt-to-equity is not treated as low risk.")
    elif latest and latest.total_debt == 0:
        add("Leverage is within the heuristic", True, "Reported total debt is zero.")
    elif de and de.value is not None and de.interpretable:
        add(
            "Leverage is within the heuristic",
            de.value <= HEALTH.debt_to_equity,
            f"Debt to equity is {de.value:.2f}. Threshold is {HEALTH.debt_to_equity:.2f}.",
        )
    else:
        add("Leverage is within the heuristic", None, "Debt to equity is unavailable.")

    if not financial:
        cover = found.get("interest_coverage")
        if latest and latest.total_debt == 0:
            add("Interest coverage is adequate", True, "No debt, so interest coverage is not a constraint.")
        elif cover and cover.value is not None:
            add(
                "Interest coverage is adequate",
                cover.value >= HEALTH.interest_coverage,
                f"Interest coverage is {cover.value:.2f}. Threshold is {HEALTH.interest_coverage:.1f}.",
            )
        else:
            add("Interest coverage is adequate", None, "Interest coverage is unavailable.")

    if latest and latest.operating_cash_flow is not None:
        add(
            "Operating cash flow is positive",
            latest.operating_cash_flow > 0,
            f"Operating cash flow is {latest.operating_cash_flow:,.0f}.",
        )
    else:
        add("Operating cash flow is positive", None, "Operating cash flow is unavailable.")

    if latest and latest.free_cash_flow is not None:
        add(
            "Free cash flow is positive",
            latest.free_cash_flow > 0,
            f"Free cash flow is {latest.free_cash_flow:,.0f}.",
        )
    else:
        add("Free cash flow is positive", None, "Free cash flow is unavailable.")

    ocf_ratio = found.get("ocf_to_net_income")
    if latest and latest.net_income is not None and latest.net_income > 0 and latest.operating_cash_flow is not None:
        supported = latest.operating_cash_flow > 0 and (
            ocf_ratio.value is not None and ocf_ratio.value >= HEALTH.ocf_to_net_income
        )
        shown = f"{ocf_ratio.value:.2f}" if ocf_ratio and ocf_ratio.value is not None else "unavailable"
        add(
            "Earnings are supported by cash",
            supported,
            f"Operating cash flow / net income is {shown}. Threshold is {HEALTH.ocf_to_net_income:.1f}.",
        )
    elif latest and latest.net_income is not None and latest.net_income <= 0:
        add("Earnings are supported by cash", None, "Net income is not positive, so cash support is not scored this way.")
    else:
        add("Earnings are supported by cash", None, "Cash-support ratio is unavailable.")

    evaluated = [item for item in checks if item[1] is not None]
    passed = [item for item in evaluated if item[1]]
    missing = [item[2] for item in checks if item[1] is None]
    strengths = [f"{item[0]}. {item[2]}" for item in passed]
    weaknesses = [f"{item[0]} failed. {item[2]}" for item in evaluated if not item[1]]

    minimum = HEALTH.financial_company_min_checks if financial else HEALTH.min_checks
    if len(evaluated) < minimum:
        label = "INSUFFICIENT_DATA"
        score = None
    else:
        score = len(passed) / len(evaluated)
        if score >= HEALTH.strong:
            label = "STRONG"
        elif score >= HEALTH.solid:
            label = "SOLID"
        elif score >= HEALTH.mixed:
            label = "MIXED"
        else:
            label = "WEAK"

    evidence = [f"{item[0]}: {'pass' if item[1] else 'fail'}. {item[2]}" for item in evaluated]
    return HealthResult(
        label=label,
        score=score,
        basis="financial_company_heuristic" if financial else "general_heuristic",
        checks_passed=len(passed),
        checks_evaluated=len(evaluated),
        metrics=metrics,
        strengths=strengths,
        weaknesses=weaknesses,
        missing=missing,
        evidence=evidence,
        history=history_points(annual),
    )
