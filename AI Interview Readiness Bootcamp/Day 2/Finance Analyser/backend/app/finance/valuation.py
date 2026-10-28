"""Blend a DCF and peer multiples into one valuation label. Thresholds live in thresholds.py."""

from __future__ import annotations

import statistics

from app.domain.models import (
    Assumption,
    AssumptionOverrides,
    MarketSnapshot,
    PeerMultiple,
    PeriodFinancials,
    ScenarioResult,
    ValuationLabel,
    ValuationResult,
)
from app.finance.dcf import (
    assumption,
    build_dcf,
    cost_of_equity,
    default_terminal_growth,
    historical_ratio,
    historical_tax_rate,
    upside_percent,
    wacc,
)
from app.finance.mathutil import clamp, pct_change, safe_div
from app.finance.peers import implied_share_price, peer_group_is_thin, summarize
from app.finance.ratios import net_debt
from app.finance.thresholds import VALUATION


def classify_upside(upside: float | None) -> ValuationLabel:
    if upside is None:
        return "INSUFFICIENT_DATA"
    if upside > VALUATION.significant_upside:
        return "SIGNIFICANTLY_UNDERVALUED"
    if upside > VALUATION.slight_upside:
        return "SLIGHTLY_UNDERVALUED"
    if upside >= VALUATION.slight_downside:
        return "FAIRLY_VALUED"
    if upside >= VALUATION.significant_downside:
        return "SLIGHTLY_OVERVALUED"
    return "SIGNIFICANTLY_OVERVALUED"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def _growth_rates(annual: list[PeriodFinancials], years: int, override: float | None) -> tuple[list[float] | None, Assumption]:
    if override is not None:
        return [override] * years, assumption(
            "revenue_growth",
            "Revenue growth",
            override,
            "analyst_input",
            "Applied to every forecast year because the user supplied one rate.",
        )
    observed: list[float] = []
    for previous, current in zip(annual, annual[1:]):
        change = pct_change(current.revenue, previous.revenue)
        if change is not None:
            observed.append(change)
    if not observed:
        return None, assumption(
            "revenue_growth",
            "Revenue growth",
            None,
            "historical",
            "Fewer than two annual revenue figures are available, so no growth rate was invented.",
        )
    raw = _median(observed[-3:])
    assert raw is not None
    used = clamp(raw, -0.05, 0.25)
    return [used] * years, assumption(
        "revenue_growth",
        "Revenue growth",
        used,
        "historical",
        f"Median of the latest {min(3, len(observed))} annual growth rates is {raw:.1%}. "
        f"The forecast uses {used:.1%} after clamping to the range -5% to 25%.",
    )


def _ratio_assumption(
    key: str,
    label: str,
    override: float | None,
    historical: float | None,
    missing: str,
) -> tuple[float | None, Assumption]:
    if override is not None:
        return override, assumption(key, label, override, "analyst_input", "Supplied by the user.")
    if historical is None:
        return None, assumption(key, label, None, "historical", missing)
    return historical, assumption(key, label, historical, "historical", "Median of up to three latest annual observations.")


def assemble_valuation(
    annual: list[PeriodFinancials],
    market: MarketSnapshot,
    peers: list[PeerMultiple],
    peer_selection: str,
    overrides: AssumptionOverrides | None = None,
) -> ValuationResult:
    overrides = overrides or AssumptionOverrides()
    years = min(max(overrides.forecast_years, 3), 7)
    assumptions: list[Assumption] = []
    limitations: list[str] = []
    latest = annual[-1] if annual else None

    growth, growth_assumption = _growth_rates(annual, years, overrides.revenue_growth)
    assumptions.append(growth_assumption)

    margin_hist = None
    if latest and latest.revenue:
        margin_hist = safe_div(latest.operating_income, latest.revenue)
    margin, margin_assumption = _ratio_assumption(
        "operating_margin",
        "Operating margin",
        overrides.operating_margin,
        margin_hist,
        "Operating margin is unavailable, so FCFF was not built from an invented margin.",
    )
    assumptions.append(margin_assumption)

    if overrides.tax_rate is not None:
        tax: float | None = overrides.tax_rate
        assumptions.append(assumption("tax_rate", "Tax rate", tax, "analyst_input", "Supplied by the user."))
    else:
        tax, tax_reason = historical_tax_rate(annual)
        if tax is None and market.currency and market.currency.upper() == "USD":
            tax = 0.21
            tax_reason = "No usable effective rate. 21% is a US statutory model estimate, not the company's guidance."
            source = "model_estimate"
        else:
            source = "historical"
        assumptions.append(assumption("tax_rate", "Tax rate", tax, source, tax_reason))

    def ratio_over_revenue(getter) -> float | None:
        return historical_ratio(
            annual,
            lambda period: safe_div(getter(period), period.revenue) if period.revenue else None,
        )

    da, da_assumption = _ratio_assumption(
        "da_pct_revenue",
        "Depreciation and amortization / revenue",
        overrides.da_pct_revenue,
        ratio_over_revenue(lambda period: period.depreciation),
        "Depreciation is unavailable, so it was not set to zero.",
    )
    capex, capex_assumption = _ratio_assumption(
        "capex_pct_revenue",
        "Capital expenditure / revenue",
        overrides.capex_pct_revenue,
        ratio_over_revenue(lambda period: period.capex),
        "Capital expenditure is unavailable, so it was not set to zero.",
    )
    nwc_hist = None
    if latest and latest.revenue and latest.current_assets is not None and latest.current_liabilities is not None:
        nwc_hist = (latest.current_assets - latest.current_liabilities) / latest.revenue
    nwc, nwc_assumption = _ratio_assumption(
        "nwc_pct_revenue",
        "Net working capital / revenue",
        overrides.nwc_pct_revenue,
        nwc_hist,
        "Working capital is unavailable, so the change in NWC was not assumed to be zero.",
    )
    assumptions.extend([da_assumption, capex_assumption, nwc_assumption])

    discount, discount_note, discount_kind, discount_assumptions = _discount(annual, market, overrides, tax)
    assumptions.extend(discount_assumptions)

    if overrides.terminal_growth is not None:
        terminal = overrides.terminal_growth
        assumptions.append(assumption("terminal_growth", "Terminal growth", terminal, "analyst_input", "Supplied by the user."))
    else:
        terminal, terminal_reason = default_terminal_growth(market.currency)
        assumptions.append(assumption("terminal_growth", "Terminal growth", terminal, "model_estimate", terminal_reason))

    debt_value, debt_note = (None, "No annual statement.") if latest is None else net_debt(latest)
    bridge = debt_value
    if latest and bridge is not None:
        extra = 0.0
        if latest.minority_interest:
            extra += latest.minority_interest
        if latest.preferred_stock:
            extra += latest.preferred_stock
        bridge = bridge + extra
        if debt_note:
            limitations.append(debt_note)
        if latest.minority_interest is None and latest.preferred_stock is None:
            limitations.append("Minority interest and preferred stock were not reported, so they are not in the equity bridge.")
    elif debt_note:
        limitations.append(debt_note)

    fcff_ready = None not in (growth, margin, tax, da, capex, nwc) and discount_kind in {"wacc", "user"}
    if fcff_ready:
        model = "fcff_wacc"
        rate = discount
        rate_source = discount_note
    else:
        model = "fcfe_cost_of_equity"
        rate = _cost_of_equity_value(discount_assumptions) if overrides.discount_rate is None else overrides.discount_rate
        rate_source = (
            "user-supplied discount rate applied to levered free cash flow"
            if overrides.discount_rate is not None
            else "cost of equity, because an enterprise WACC model was not supported"
        )
        if discount_kind != "wacc":
            limitations.append(discount_note)

    dcf = build_dcf(
        annual,
        shares=market.shares,
        net_debt=bridge,
        discount_rate=rate,
        discount_source=rate_source,
        terminal_growth=terminal,
        growth_rates=growth or [],
        ebit_margin=margin,
        tax_rate=tax,
        da_pct=da,
        capex_pct=capex,
        nwc_pct=nwc,
        model=model,
    )
    dcf.limitations = limitations + dcf.limitations

    usable = [peer for peer in peers if peer.excluded_reason is None]
    medians, means = summarize(peers)
    excluded = [f"{peer.ticker}: {peer.excluded_reason}" for peer in peers if peer.excluded_reason]
    peer_value = None
    peer_notes: list[str] = []
    if peer_group_is_thin(len(usable)):
        limitations.append(
            f"Only {len(usable)} peers have usable multiples. The minimum for a peer value is {VALUATION.min_peers}, so no peer value was used."
        )
    elif latest is not None:
        eps = latest.eps
        if eps is None and market.shares:
            eps = safe_div(latest.net_income, market.shares)
        peer_value, peer_notes = implied_share_price(
            medians,
            eps=eps,
            revenue=latest.revenue,
            shares=market.shares,
            equity=latest.equity,
            ebitda=latest.ebitda,
            net_debt=bridge,
        )
        if peer_value is None:
            limitations.append("Peer multiples were available but none mapped to a per-share value.")

    dcf_value = dcf.intrinsic_value_per_share if dcf.status == "ok" else None
    if dcf.status == "unreliable" and dcf.intrinsic_value_per_share is not None:
        limitations.append("The DCF produced a number, but its status is unreliable, so that number was not used in the valuation label.")

    if dcf_value is not None and peer_value is not None:
        intrinsic = VALUATION.dcf_weight * dcf_value + VALUATION.peer_weight * peer_value
        method = f"{VALUATION.dcf_weight:.0%} DCF and {VALUATION.peer_weight:.0%} median peer-implied price. The peer median is not treated as fair value by itself."
    elif dcf_value is not None:
        intrinsic = dcf_value
        method = "DCF only. The peer group did not support a second value."
    elif peer_value is not None:
        intrinsic = peer_value
        method = "Peer-implied price only. The DCF was unavailable or unreliable and was not used for the label."
    else:
        intrinsic = None
        method = "Neither the DCF nor the peer set supported a value, so no valuation label is issued."

    upside = upside_percent(intrinsic, market.price)
    label = classify_upside(upside)
    difference = None if intrinsic is None or market.price is None else intrinsic - market.price
    scenarios = _scenarios(
        annual,
        market,
        growth,
        margin,
        tax,
        da,
        capex,
        nwc,
        rate,
        terminal,
        bridge,
        model,
        rate_source,
    )
    if peer_notes:
        limitations.append("Peer-implied price uses: " + "; ".join(peer_notes) + ".")

    target = None
    if latest is not None:
        from app.finance.peers import multiple_set

        target = multiple_set(
            ticker=market.ticker,
            name=market.company_name,
            price=market.price,
            market_cap=market.market_cap,
            enterprise_value=market.enterprise_value,
            revenue=latest.revenue,
            net_income=latest.net_income,
            equity=latest.equity,
            ebitda=latest.ebitda,
        )

    return ValuationResult(
        label=label,
        method_used=method,
        intrinsic_value_per_share=intrinsic,
        current_price=market.price,
        difference=difference,
        upside_percent=upside,
        dcf=dcf,
        peers=peers,
        peer_median=medians,
        peer_mean=means,
        peer_implied_value=peer_value,
        peer_selection=peer_selection,
        excluded_peers=excluded,
        target_multiples=target,
        scenarios=scenarios,
        assumptions=assumptions,
        limitations=limitations,
    )


def _latest_interest(annual: list[PeriodFinancials]) -> tuple[float | None, str | None]:
    for period in reversed(annual):
        if period.interest_expense and period.interest_expense > 0:
            return period.interest_expense, period.period_end
    return None, None


def _cost_of_equity_value(items: list[Assumption]) -> float | None:
    for item in items:
        if item.key == "cost_of_equity" and isinstance(item.value, float):
            return item.value
    return None


def _discount(
    annual: list[PeriodFinancials],
    market: MarketSnapshot,
    overrides: AssumptionOverrides,
    tax: float | None,
) -> tuple[float | None, str, str, list[Assumption]]:
    items: list[Assumption] = []
    if market.beta is None:
        beta = 1.0
        items.append(assumption("beta", "Beta", beta, "model_estimate", "The provider did not supply beta. 1.0 is a placeholder, not a measured beta."))
    else:
        beta = market.beta
        items.append(assumption("beta", "Beta", beta, "market", "Beta reported by the market data provider."))
    ke = cost_of_equity(overrides.risk_free_rate, beta, overrides.equity_risk_premium)
    items.append(
        assumption(
            "cost_of_equity",
            "Cost of equity",
            ke,
            "model_estimate",
            f"CAPM: {overrides.risk_free_rate:.2%} + beta × {overrides.equity_risk_premium:.2%}. "
            "The risk-free rate and premium are configured assumptions, not live bond quotes.",
        )
    )
    if overrides.discount_rate is not None:
        items.append(assumption("discount_rate", "Discount rate", overrides.discount_rate, "analyst_input", "Supplied by the user and used for the selected DCF model."))
        return overrides.discount_rate, "user-supplied discount rate", "user", items

    latest = annual[-1] if annual else None
    debt = latest.total_debt if latest else None
    interest, interest_period = _latest_interest(annual)
    if debt == 0:
        items.append(assumption("discount_rate", "Discount rate", ke, "model_estimate", "Reported debt is zero, so WACC equals the cost of equity."))
        return ke, "WACC equals the cost of equity because reported debt is zero", "wacc", items
    if debt and debt > 0 and market.market_cap and market.market_cap > 0 and interest and tax is not None:
        kd = interest / debt
        capital = market.market_cap + debt
        rate = wacc(ke, kd, market.market_cap / capital, debt / capital, tax)
        period_note = (
            "Interest expense / latest total debt."
            if latest and interest_period == latest.period_end
            else f"Interest expense from {interest_period} / latest total debt. Later income statements did not report interest expense."
        )
        items.append(assumption("cost_of_debt", "Cost of debt", kd, "historical", period_note + " This is an accounting yield, not a market yield."))
        items.append(assumption("discount_rate", "WACC", rate, "model_estimate", "Equity weight uses market cap. Debt weight uses reported total debt, not a market value of debt."))
        return rate, "WACC from CAPM equity cost and the accounting cost of debt", "wacc", items
    items.append(
        assumption(
            "discount_rate",
            "Discount rate",
            ke,
            "model_estimate",
            "WACC was not calculated because debt, interest expense, tax, or market cap is missing. Cost of equity is available only for an equity DCF.",
        )
    )
    return ke, "WACC was not calculated because the capital-structure inputs are incomplete.", "ke_only", items


def _scenarios(
    annual,
    market,
    growth,
    margin,
    tax,
    da,
    capex,
    nwc,
    rate,
    terminal,
    bridge,
    model,
    rate_source,
) -> list[ScenarioResult]:
    if not growth or rate is None:
        return [
            ScenarioResult(
                name=name,
                intrinsic_value_per_share=None,
                upside_percent=None,
                assumptions=[],
                note="Scenarios were not run because the base forecast is missing a growth rate or a discount rate.",
            )
            for name in ("bull", "base", "bear")
        ]
    shifts = {
        "bull": (0.03, 0.02, -0.005, 0.005),
        "base": (0.0, 0.0, 0.0, 0.0),
        "bear": (-0.03, -0.02, 0.005, -0.005),
    }
    results = []
    for name, (growth_delta, margin_delta, rate_delta, terminal_delta) in shifts.items():
        scenario_growth = [clamp(item + growth_delta, -0.2, 0.4) for item in growth]
        scenario_rate = rate + rate_delta
        scenario_terminal = max(0.0, terminal + terminal_delta)
        scenario_margin = None if margin is None else margin + margin_delta
        if scenario_terminal >= scenario_rate:
            results.append(
                ScenarioResult(
                    name=name,  # type: ignore[arg-type]
                    intrinsic_value_per_share=None,
                    upside_percent=None,
                    assumptions=[],
                    note="Skipped because terminal growth would not be below the discount rate.",
                )
            )
            continue
        dcf = build_dcf(
            annual,
            shares=market.shares,
            net_debt=bridge,
            discount_rate=scenario_rate,
            discount_source=rate_source,
            terminal_growth=scenario_terminal,
            growth_rates=scenario_growth,
            ebit_margin=scenario_margin,
            tax_rate=tax,
            da_pct=da,
            capex_pct=capex,
            nwc_pct=nwc,
            model=model,
        )
        value = dcf.intrinsic_value_per_share if dcf.status == "ok" else None
        results.append(
            ScenarioResult(
                name=name,  # type: ignore[arg-type]
                intrinsic_value_per_share=value,
                upside_percent=upside_percent(value, market.price),
                assumptions=[
                    assumption("revenue_growth", "Revenue growth", scenario_growth[0], "model_estimate", "Base growth shifted for this scenario."),
                    assumption("discount_rate", "Discount rate", scenario_rate, "model_estimate", "Base discount rate shifted for this scenario."),
                    assumption("terminal_growth", "Terminal growth", scenario_terminal, "model_estimate", "Base terminal growth shifted for this scenario."),
                ],
                note=dcf.methodology if value is not None else "; ".join(dcf.limitations) or "Scenario did not produce a usable value.",
            )
        )
    return results
