"""Discounted cash flow. FCFF is discounted at WACC. Levered FCF is discounted at the cost of equity."""

from __future__ import annotations

from app.domain.models import Assumption, DCFResult, ForecastYear, PeriodFinancials, SensitivityCell
from app.finance.mathutil import safe_div

DEVELOPED_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"}


def cost_of_equity(risk_free: float, beta: float, equity_risk_premium: float) -> float:
    """CAPM: risk-free rate + beta × equity risk premium."""
    return risk_free + beta * equity_risk_premium


def wacc(
    cost_of_equity_rate: float,
    cost_of_debt: float,
    equity_weight: float,
    debt_weight: float,
    tax_rate: float,
) -> float:
    """WACC = E/V × cost of equity + D/V × cost of debt × (1 − tax rate)."""
    return equity_weight * cost_of_equity_rate + debt_weight * cost_of_debt * (1 - tax_rate)


def project_fcff(
    revenue0: float,
    growth_rates: list[float],
    ebit_margin: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
) -> list[float]:
    """FCFF = EBIT × (1 − tax) + depreciation − capex − change in net working capital.

    Opening net working capital is revenue0 × nwc_pct, so the first year's change comes from growth.
    """
    revenue = revenue0
    nwc = revenue0 * nwc_pct
    flows: list[float] = []
    for growth in growth_rates:
        revenue = revenue * (1 + growth)
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)
        depreciation = revenue * da_pct
        capex = revenue * capex_pct
        next_nwc = revenue * nwc_pct
        delta_nwc = next_nwc - nwc
        nwc = next_nwc
        flows.append(nopat + depreciation - capex - delta_nwc)
    return flows


def present_value(cashflows: list[float], discount_rate: float, terminal_growth: float) -> tuple[float, float, float, list[ForecastYear]]:
    """Discount explicit cash flows and a Gordon growth terminal value.

    Terminal value = final cash flow × (1 + g) / (discount rate − g).
    Both the cash flow and the terminal value are discounted from the end of each year.
    """
    if discount_rate <= terminal_growth:
        raise ValueError("Discount rate must be greater than the terminal growth rate.")
    if not cashflows:
        raise ValueError("At least one forecast cash flow is required.")
    terminal = cashflows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    years: list[ForecastYear] = []
    pv_flows = 0.0
    for index, flow in enumerate(cashflows, start=1):
        factor = 1 / (1 + discount_rate) ** index
        pv = flow * factor
        pv_flows += pv
        years.append(
            ForecastYear(
                year=index,
                free_cash_flow=flow,
                discount_factor=factor,
                present_value=pv,
            )
        )
    pv_terminal = terminal * years[-1].discount_factor
    return pv_flows + pv_terminal, terminal, pv_terminal, years


def upside_percent(intrinsic: float | None, price: float | None) -> float | None:
    """(Intrinsic value per share / current price − 1) × 100."""
    if intrinsic is None or price is None or price <= 0:
        return None
    return (intrinsic / price - 1) * 100


def default_terminal_growth(currency: str | None) -> tuple[float, str]:
    if currency and currency.upper() in DEVELOPED_CURRENCIES:
        return 0.025, f"2.5% model estimate for {currency.upper()}, below a long-run developed-market nominal growth rate."
    if currency:
        return 0.04, f"4% model estimate because {currency.upper()} is not in the developed-currency list. This is not a forecast."
    return 0.025, "2.5% model estimate because the reporting currency is unknown."


def historical_tax_rate(annual: list[PeriodFinancials]) -> tuple[float | None, str]:
    rates: list[float] = []
    for period in annual[-3:]:
        if period.pretax_income and period.pretax_income > 0 and period.tax_provision is not None:
            rate = period.tax_provision / period.pretax_income
            if 0 <= rate < 0.6:
                rates.append(rate)
    if not rates:
        return None, "No usable effective tax rate in the last three annual periods."
    median = sorted(rates)[len(rates) // 2]
    return median, "Median effective tax rate over available recent annual periods with positive pretax income."


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def historical_ratio(annual: list[PeriodFinancials], getter) -> float | None:
    values = []
    for period in annual[-3:]:
        ratio = getter(period)
        if ratio is not None:
            values.append(ratio)
    if not values:
        return None
    return _median(values)


def build_dcf(
    annual: list[PeriodFinancials],
    *,
    shares: float | None,
    net_debt: float | None,
    discount_rate: float | None,
    discount_source: str,
    terminal_growth: float,
    growth_rates: list[float],
    ebit_margin: float | None,
    tax_rate: float | None,
    da_pct: float | None,
    capex_pct: float | None,
    nwc_pct: float | None,
    model: str,
) -> DCFResult:
    limitations: list[str] = []
    if discount_rate is None:
        return DCFResult(
            status="unavailable",
            model="none",
            methodology="No DCF was run because the discount rate could not be calculated or supplied.",
            limitations=["Discount rate is missing."],
        )
    if terminal_growth >= discount_rate:
        return DCFResult(
            status="unavailable",
            model="none",
            methodology="No DCF was run because terminal growth is not below the discount rate.",
            discount_rate=discount_rate,
            terminal_growth=terminal_growth,
            limitations=["Terminal growth must be lower than the discount rate."],
        )
    if shares is None or shares <= 0:
        limitations.append("Share count is missing, so a per-share value cannot be calculated.")

    cashflows: list[float] = []
    methodology = ""
    chosen: str = "none"
    if model == "fcff_wacc":
        latest = annual[-1]
        if (
            latest.revenue
            and latest.revenue > 0
            and ebit_margin is not None
            and tax_rate is not None
            and da_pct is not None
            and capex_pct is not None
            and nwc_pct is not None
        ):
            cashflows = project_fcff(
                latest.revenue,
                growth_rates,
                ebit_margin,
                tax_rate,
                da_pct,
                capex_pct,
                nwc_pct,
            )
            chosen = "fcff_wacc"
            methodology = (
                "Enterprise DCF. FCFF = EBIT × (1 − tax rate) + depreciation and amortization "
                "− capital expenditure − change in net working capital. EBIT is revenue × the operating-margin "
                f"assumption. Cash flows are discounted at {discount_source}."
            )
        else:
            limitations.append("FCFF inputs are incomplete, so the enterprise DCF was not run.")
    if not cashflows and model in {"fcfe_cost_of_equity", "fcff_wacc"}:
        latest_fcf = annual[-1].free_cash_flow if annual else None
        if latest_fcf is not None and latest_fcf <= 0:
            limitations.append(
                "Latest free cash flow is not positive. A growth DCF on a negative base would invent a path back to cash generation, so it was not run."
            )
        elif latest_fcf is not None and growth_rates:
            flow = latest_fcf
            for growth in growth_rates:
                flow = flow * (1 + growth)
                cashflows.append(flow)
            chosen = "fcfe_cost_of_equity"
            methodology = (
                "Equity DCF on reported free cash flow (operating cash flow minus capital expenditure). "
                "This cash flow is treated as levered, so it is discounted at the cost of equity and debt is not subtracted again. "
                f"Discount source: {discount_source}."
            )
            limitations.append(
                "This is a simplified equity DCF. It grows the latest free cash flow at the revenue-growth assumption and does not rebuild working capital."
            )

    if not cashflows or chosen == "none":
        return DCFResult(
            status="unavailable",
            model="none",
            methodology=methodology or "No supported DCF could be built from the available statements.",
            discount_rate=discount_rate,
            terminal_growth=terminal_growth,
            limitations=limitations or ["Forecast cash flows are unavailable."],
        )

    if cashflows[-1] <= 0:
        return DCFResult(
            status="unreliable",
            model=chosen,  # type: ignore[arg-type]
            methodology=methodology,
            discount_rate=discount_rate,
            terminal_growth=terminal_growth,
            limitations=limitations + ["The final forecast cash flow is not positive, so terminal value was not capitalised."],
        )

    enterprise, terminal, pv_terminal, years = present_value(cashflows, discount_rate, terminal_growth)
    for index, year in enumerate(years):
        if annual and annual[-1].revenue and growth_rates:
            revenue = annual[-1].revenue
            for growth in growth_rates[: index + 1]:
                revenue *= 1 + growth
            year.revenue = revenue

    equity_value: float | None
    enterprise_value: float | None
    if chosen == "fcff_wacc":
        enterprise_value = enterprise
        if net_debt is None:
            equity_value = None
            limitations.append("Net debt is unavailable, so enterprise value was not bridged to equity value.")
        else:
            equity_value = enterprise_value - net_debt
        value_base = enterprise_value
    else:
        enterprise_value = None
        equity_value = enterprise
        value_base = equity_value

    per_share = safe_div(equity_value, shares)
    terminal_share = safe_div(pv_terminal, value_base)
    volatile = _fcf_volatile(annual)
    status = "unreliable" if volatile or per_share is None else "ok"
    if volatile:
        limitations.append("Free cash flow changed sign or swung sharply across the available years. Treat the point estimate as weak.")
    if any(flow < 0 for flow in cashflows[:-1]):
        limitations.append("One or more explicit forecast years have negative cash flow.")

    sensitivity = _sensitivity(cashflows, discount_rate, terminal_growth, net_debt if chosen == "fcff_wacc" else 0.0, shares, chosen)
    margin_sensitivity: list[dict[str, float | None]] = []
    if chosen == "fcff_wacc" and annual and annual[-1].revenue and ebit_margin is not None and tax_rate is not None:
        margin_sensitivity = _margin_sensitivity(
            annual[-1].revenue,
            growth_rates,
            ebit_margin,
            tax_rate,
            da_pct or 0,
            capex_pct or 0,
            nwc_pct or 0,
            discount_rate,
            terminal_growth,
            net_debt,
            shares,
        )

    return DCFResult(
        status=status,
        model=chosen,  # type: ignore[arg-type]
        methodology=methodology,
        intrinsic_value_per_share=per_share,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
        terminal_value=terminal,
        terminal_value_share=terminal_share,
        forecast=years,
        sensitivity=sensitivity,
        margin_sensitivity=margin_sensitivity,
        limitations=limitations,
    )


def _fcf_volatile(annual: list[PeriodFinancials]) -> bool:
    flows = [period.free_cash_flow for period in annual if period.free_cash_flow is not None]
    if len(flows) < 3:
        return False
    positives = sum(flow > 0 for flow in flows)
    return positives not in (0, len(flows))


def _per_share_from_value(total: float, net_debt: float | None, shares: float | None, model: str) -> float | None:
    if model == "fcff_wacc":
        if net_debt is None:
            return None
        equity = total - net_debt
    else:
        equity = total
    return safe_div(equity, shares)


def _sensitivity(
    cashflows: list[float],
    discount_rate: float,
    terminal_growth: float,
    net_debt: float | None,
    shares: float | None,
    model: str,
) -> list[SensitivityCell]:
    cells: list[SensitivityCell] = []
    if shares is None or shares <= 0:
        return cells
    for step in (-0.02, -0.01, 0.0, 0.01, 0.02):
        rate = round(discount_rate + step, 4)
        if rate <= 0:
            continue
        for growth_step in (-0.01, -0.005, 0.0, 0.005, 0.01):
            growth = round(terminal_growth + growth_step, 4)
            if growth < 0 or growth >= rate:
                continue
            total, _, _, _ = present_value(cashflows, rate, growth)
            value = _per_share_from_value(total, net_debt, shares, model)
            if value is None:
                continue
            cells.append(SensitivityCell(discount_rate=rate, terminal_growth=growth, value_per_share=value))
    return cells


def _margin_sensitivity(
    revenue0: float,
    growth_rates: list[float],
    ebit_margin: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    discount_rate: float,
    terminal_growth: float,
    net_debt: float | None,
    shares: float | None,
) -> list[dict[str, float | None]]:
    rows = []
    for delta in (-0.02, 0.0, 0.02):
        flows = project_fcff(revenue0, growth_rates, ebit_margin + delta, tax_rate, da_pct, capex_pct, nwc_pct)
        if not flows or flows[-1] <= 0 or discount_rate <= terminal_growth:
            rows.append({"operating_margin": ebit_margin + delta, "value_per_share": None})
            continue
        total, _, _, _ = present_value(flows, discount_rate, terminal_growth)
        rows.append(
            {
                "operating_margin": ebit_margin + delta,
                "value_per_share": _per_share_from_value(total, net_debt, shares, "fcff_wacc"),
            }
        )
    return rows


def assumption(key: str, label: str, value, source: str, rationale: str) -> Assumption:
    return Assumption(key=key, label=label, value=value, source=source, rationale=rationale)  # type: ignore[arg-type]
