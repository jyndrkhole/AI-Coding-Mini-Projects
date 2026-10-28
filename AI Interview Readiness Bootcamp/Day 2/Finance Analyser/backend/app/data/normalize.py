"""Turn yfinance statement frames into one period schema. Missing rows stay None."""

from __future__ import annotations

from app.domain.models import PeriodFinancials
from app.finance.mathutil import clean_number

ROW_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "Operating Revenue", "Revenue"),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income", "Operating Income Loss"),
    "ebit": ("EBIT",),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "interest_expense": ("Interest Expense", "Interest Expense Non Operating"),
    "tax_provision": ("Tax Provision",),
    "pretax_income": ("Pretax Income",),
    "eps": ("Diluted EPS", "Basic EPS"),
    "depreciation_is": ("Reconciled Depreciation", "Depreciation And Amortization"),
    "cash": ("Cash And Cash Equivalents",),
    "cash_broad": ("Cash Cash Equivalents And Short Term Investments", "Cash And Short Term Investments"),
    "total_assets": ("Total Assets",),
    "current_assets": ("Current Assets",),
    "inventory": ("Inventory",),
    "total_liabilities": ("Total Liabilities Net Minority Interest", "Total Liabilities"),
    "current_liabilities": ("Current Liabilities",),
    "total_debt": ("Total Debt",),
    "equity": ("Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"),
    "shares": ("Ordinary Shares Number", "Share Issued"),
    "minority_interest": ("Minority Interest", "Minority Interest Balance Sheet"),
    "preferred_stock": ("Preferred Stock",),
    "operating_cash_flow": ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"),
    "capex": ("Capital Expenditure", "Purchase Of PPE"),
    "free_cash_flow": ("Free Cash Flow",),
    "depreciation_cf": ("Depreciation And Amortization", "Depreciation Amortization Depletion"),
    "change_in_working_capital": ("Change In Working Capital",),
    "dividends": ("Common Stock Dividend Paid", "Cash Dividends Paid"),
}


def _lookup(frame) -> dict[str, object]:
    if frame is None:
        return {}
    try:
        if frame.empty:
            return {}
    except AttributeError:
        return {}
    return {str(index).strip().lower(): index for index in frame.index}


def _cell(frame, lookup: dict[str, object], names: tuple[str, ...], column) -> tuple[float | None, str | None]:
    if frame is None or not lookup:
        return None, None
    for name in names:
        key = name.lower()
        if key in lookup:
            value = clean_number(frame.loc[lookup[key], column])
            if value is not None:
                return value, name
    return None, None


def _as_date(column) -> str:
    if hasattr(column, "date"):
        try:
            return column.date().isoformat()
        except Exception:
            pass
    text = str(column)
    return text[:10]


def _positive_spend(value: float | None) -> float | None:
    if value is None:
        return None
    return abs(value)


def frames_to_periods(income, balance, cashflow, period_type: str, limit: int) -> list[PeriodFinancials]:
    frames = [frame for frame in (income, balance, cashflow) if frame is not None and not getattr(frame, "empty", True)]
    if not frames:
        return []
    dates = sorted({_as_date(column) for frame in frames for column in frame.columns})
    periods: list[PeriodFinancials] = []
    lookups = {id(frame): _lookup(frame) for frame in frames}
    for stamp in dates:
        def cell(frame, key: str) -> tuple[float | None, str | None]:
            if frame is None or getattr(frame, "empty", True):
                return None, None
            match = None
            for column in frame.columns:
                if _as_date(column) == stamp:
                    match = column
                    break
            if match is None:
                return None, None
            return _cell(frame, lookups[id(frame)], ROW_ALIASES[key], match)

        revenue, _ = cell(income, "revenue")
        gross, _ = cell(income, "gross_profit")
        operating, _ = cell(income, "operating_income")
        ebit, _ = cell(income, "ebit")
        ebitda, _ = cell(income, "ebitda")
        net_income, _ = cell(income, "net_income")
        interest, _ = cell(income, "interest_expense")
        tax, _ = cell(income, "tax_provision")
        pretax, _ = cell(income, "pretax_income")
        eps, _ = cell(income, "eps")
        da_is, _ = cell(income, "depreciation_is")
        cash, cash_name = cell(balance, "cash")
        cash_definition = cash_name
        if cash is None:
            cash, cash_name = cell(balance, "cash_broad")
            cash_definition = cash_name
        assets, _ = cell(balance, "total_assets")
        current_assets, _ = cell(balance, "current_assets")
        inventory, _ = cell(balance, "inventory")
        liabilities, _ = cell(balance, "total_liabilities")
        current_liabilities, _ = cell(balance, "current_liabilities")
        debt, _ = cell(balance, "total_debt")
        equity, _ = cell(balance, "equity")
        shares, _ = cell(balance, "shares")
        minority, _ = cell(balance, "minority_interest")
        preferred, _ = cell(balance, "preferred_stock")
        ocf, _ = cell(cashflow, "operating_cash_flow")
        capex_raw, _ = cell(cashflow, "capex")
        reported_fcf, _ = cell(cashflow, "free_cash_flow")
        da_cf, _ = cell(cashflow, "depreciation_cf")
        nwc_change, _ = cell(cashflow, "change_in_working_capital")
        dividends_raw, _ = cell(cashflow, "dividends")
        capex = _positive_spend(capex_raw)
        depreciation = da_cf if da_cf is not None else da_is
        if ocf is not None and capex is not None:
            free_cash_flow = ocf - capex
        else:
            free_cash_flow = reported_fcf
        if all(
            value is None
            for value in (revenue, net_income, assets, equity, ocf, free_cash_flow)
        ):
            continue
        periods.append(
            PeriodFinancials(
                period_end=stamp,
                period_type=period_type,  # type: ignore[arg-type]
                revenue=revenue,
                gross_profit=gross,
                operating_income=operating if operating is not None else ebit,
                ebit=ebit if ebit is not None else operating,
                ebitda=ebitda,
                net_income=net_income,
                interest_expense=abs(interest) if interest is not None else None,
                tax_provision=tax,
                pretax_income=pretax,
                eps=eps,
                depreciation=abs(depreciation) if depreciation is not None else None,
                cash=cash,
                cash_definition=cash_definition,
                total_assets=assets,
                current_assets=current_assets,
                inventory=inventory,
                total_liabilities=liabilities,
                current_liabilities=current_liabilities,
                total_debt=debt,
                equity=equity,
                shares=shares,
                minority_interest=minority,
                preferred_stock=preferred,
                operating_cash_flow=ocf,
                capex=capex,
                free_cash_flow=free_cash_flow,
                dividends=_positive_spend(dividends_raw),
                change_in_working_capital=nwc_change,
            )
        )
    periods.sort(key=lambda period: period.period_end)
    return periods[-limit:]
