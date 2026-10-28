"""Statement metrics. Every public function records the formula it uses."""

from __future__ import annotations

from app.domain.models import HistoryPoint, Metric, PeriodFinancials
from app.finance.mathutil import average, cagr, pct_change, safe_div


def _metric(
    key: str,
    label: str,
    value: float | None,
    unit: str,
    formula: str,
    period: str | None = None,
    note: str | None = None,
    interpretable: bool = True,
) -> Metric:
    return Metric(
        key=key,
        label=label,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        formula=formula,
        period=period,
        note=note,
        interpretable=interpretable,
    )


def net_debt(period: PeriodFinancials) -> tuple[float | None, str | None]:
    """Net debt = total debt − cash and cash equivalents."""
    if period.total_debt is None or period.cash is None:
        return None, "Total debt or cash is unavailable, so net debt is not estimated."
    return period.total_debt - period.cash, None


def working_capital(period: PeriodFinancials) -> float | None:
    """Working capital = current assets − current liabilities."""
    if period.current_assets is None or period.current_liabilities is None:
        return None
    return period.current_assets - period.current_liabilities


def build_metrics(annual: list[PeriodFinancials]) -> list[Metric]:
    """Ratios for the latest annual period, using the prior period for growth and averages."""
    if not annual:
        return []
    latest = annual[-1]
    prior = annual[-2] if len(annual) >= 2 else None
    period = latest.period_end
    metrics: list[Metric] = []

    growth = pct_change(latest.revenue, prior.revenue if prior else None)
    metrics.append(
        _metric(
            "revenue_growth",
            "Revenue growth",
            growth,
            "percent",
            "(Revenue_t − Revenue_t−1) / |Revenue_t−1|",
            period,
            None if prior else "A prior annual period is not available.",
        )
    )
    if len(annual) >= 3:
        metrics.append(
            _metric(
                "revenue_cagr",
                "Revenue CAGR",
                cagr(annual[0].revenue, latest.revenue, len(annual) - 1),
                "percent",
                "(Revenue_end / Revenue_start) ^ (1 / years) − 1",
                f"{annual[0].period_end} to {period}",
            )
        )

    metrics.append(
        _metric(
            "gross_margin",
            "Gross margin",
            safe_div(latest.gross_profit, latest.revenue),
            "percent",
            "Gross profit / Revenue",
            period,
        )
    )
    metrics.append(
        _metric(
            "operating_margin",
            "Operating margin",
            safe_div(latest.operating_income, latest.revenue),
            "percent",
            "Operating income / Revenue",
            period,
        )
    )
    metrics.append(
        _metric(
            "net_margin",
            "Net profit margin",
            safe_div(latest.net_income, latest.revenue),
            "percent",
            "Net income / Revenue",
            period,
        )
    )

    avg_equity = average(latest.equity, prior.equity if prior else None)
    equity_note = None
    equity_ok = True
    if latest.equity is not None and latest.equity <= 0:
        equity_ok = False
        equity_note = "Equity is not positive. ROE is shown but is not a return-quality signal."
    elif prior is None or prior.equity is None:
        equity_note = "Prior equity is unavailable. Ending equity is used instead of an average."
    metrics.append(
        _metric(
            "roe",
            "Return on equity",
            safe_div(latest.net_income, avg_equity),
            "percent",
            "Net income / Average shareholders' equity",
            period,
            equity_note,
            equity_ok,
        )
    )

    avg_assets = average(latest.total_assets, prior.total_assets if prior else None)
    asset_note = None if prior and prior.total_assets is not None else "Prior assets are unavailable. Ending assets are used."
    metrics.append(
        _metric(
            "roa",
            "Return on assets",
            safe_div(latest.net_income, avg_assets),
            "percent",
            "Net income / Average total assets",
            period,
            asset_note,
        )
    )

    metrics.append(
        _metric(
            "current_ratio",
            "Current ratio",
            safe_div(latest.current_assets, latest.current_liabilities),
            "ratio",
            "Current assets / Current liabilities",
            period,
        )
    )
    quick = None
    quick_note = None
    if latest.inventory is None:
        quick_note = "Inventory is unavailable, so the quick ratio is not calculated."
    else:
        quick = safe_div(
            None if latest.current_assets is None else latest.current_assets - latest.inventory,
            latest.current_liabilities,
        )
    metrics.append(
        _metric(
            "quick_ratio",
            "Quick ratio",
            quick,
            "ratio",
            "(Current assets − Inventory) / Current liabilities",
            period,
            quick_note,
        )
    )

    de = safe_div(latest.total_debt, latest.equity)
    de_note = None
    de_ok = True
    if latest.equity is not None and latest.equity <= 0:
        de_ok = False
        de_note = "Negative equity. A negative debt-to-equity ratio is not low leverage."
    metrics.append(
        _metric(
            "debt_to_equity",
            "Debt to equity",
            de,
            "ratio",
            "Total debt / Shareholders' equity",
            period,
            de_note,
            de_ok,
        )
    )

    debt, debt_note = net_debt(latest)
    metrics.append(
        _metric("net_debt", "Net debt", debt, "currency", "Total debt − Cash and cash equivalents", period, debt_note)
    )
    metrics.append(
        _metric(
            "working_capital",
            "Working capital",
            working_capital(latest),
            "currency",
            "Current assets − Current liabilities",
            period,
        )
    )

    coverage = safe_div(latest.operating_income, latest.interest_expense)
    coverage_note = None
    if latest.total_debt == 0:
        coverage_note = "Total debt is zero. Interest coverage is not applicable."
        coverage = None
    elif latest.interest_expense is None:
        coverage_note = "Interest expense is unavailable."
    metrics.append(
        _metric(
            "interest_coverage",
            "Interest coverage",
            coverage,
            "ratio",
            "Operating income / Interest expense",
            period,
            coverage_note,
        )
    )

    ocf_note = None
    if latest.net_income is not None and latest.net_income < 0:
        ocf_note = "Net income is negative, so this ratio is not an earnings-quality signal."
    metrics.append(
        _metric(
            "ocf_to_net_income",
            "Operating cash flow to net income",
            safe_div(latest.operating_cash_flow, latest.net_income),
            "ratio",
            "Operating cash flow / Net income",
            period,
            ocf_note,
            interpretable=not (latest.net_income is not None and latest.net_income < 0),
        )
    )
    metrics.append(
        _metric(
            "fcf_margin",
            "Free cash flow margin",
            safe_div(latest.free_cash_flow, latest.revenue),
            "percent",
            "Free cash flow / Revenue",
            period,
        )
    )
    metrics.append(
        _metric(
            "fcf_growth",
            "Free cash flow growth",
            pct_change(latest.free_cash_flow, prior.free_cash_flow if prior else None),
            "percent",
            "(FCF_t − FCF_t−1) / |FCF_t−1|",
            period,
            None if prior else "A prior free-cash-flow figure is not available.",
        )
    )

    payout = None
    payout_note = None
    if latest.net_income is None or latest.dividends is None:
        payout_note = "Dividends or net income are unavailable."
    elif latest.net_income <= 0:
        payout_note = "Net income is not positive, so the payout ratio is not meaningful."
    else:
        payout = latest.dividends / latest.net_income
    metrics.append(
        _metric(
            "dividend_payout",
            "Dividend payout",
            payout,
            "percent",
            "Dividends / Net income",
            period,
            payout_note,
        )
    )
    coverage_fcf = safe_div(latest.free_cash_flow, latest.dividends)
    metrics.append(
        _metric(
            "dividend_cash_coverage",
            "Dividend coverage by free cash flow",
            coverage_fcf,
            "ratio",
            "Free cash flow / Dividends",
            period,
            None if latest.dividends else "No dividend was reported for this period.",
        )
    )
    if latest.eps is not None:
        eps_growth = pct_change(latest.eps, prior.eps if prior else None)
        metrics.append(
            _metric(
                "eps_growth",
                "EPS growth",
                eps_growth,
                "percent",
                "(EPS_t − EPS_t−1) / |EPS_t−1|",
                period,
                None if prior else "A prior EPS is not available.",
            )
        )
    return metrics


def history_points(annual: list[PeriodFinancials]) -> list[HistoryPoint]:
    points: list[HistoryPoint] = []
    for period in annual:
        points.append(
            HistoryPoint(
                period=period.period_end,
                revenue=period.revenue,
                gross_profit=period.gross_profit,
                operating_income=period.operating_income,
                net_income=period.net_income,
                operating_cash_flow=period.operating_cash_flow,
                free_cash_flow=period.free_cash_flow,
                gross_margin=safe_div(period.gross_profit, period.revenue),
                operating_margin=safe_div(period.operating_income, period.revenue),
                net_margin=safe_div(period.net_income, period.revenue),
                equity=period.equity,
                total_debt=period.total_debt,
                cash=period.cash,
            )
        )
    return points
