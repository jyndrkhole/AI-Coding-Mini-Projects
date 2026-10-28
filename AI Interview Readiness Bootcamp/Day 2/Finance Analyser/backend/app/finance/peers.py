"""Peer multiples and a curated, overrideable peer universe."""

from __future__ import annotations

import statistics

from app.domain.models import PeerMultiple
from app.finance.mathutil import safe_div
from app.finance.thresholds import VALUATION

UNIVERSES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("consumer electronics", "technology hardware", "communication equipment"), ("AAPL", "SONY", "HPQ", "DELL", "LOGI", "GRMN")),
    (("semiconductor", "semiconductors"), ("NVDA", "AVGO", "AMD", "QCOM", "TXN", "AMAT", "INTC", "MU")),
    (("software", "internet content", "information technology"), ("MSFT", "ORCL", "CRM", "ADBE", "NOW", "INTU", "IBM")),
    (("internet retail", "broadline"), ("AMZN", "BABA", "JD", "MELI", "EBAY")),
    (("interactive media", "entertainment"), ("GOOGL", "META", "NFLX", "DIS", "CMCSA")),
    (("drug", "biotechnology", "pharma"), ("LLY", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "BMY")),
    (("bank",), ("JPM", "BAC", "WFC", "C", "GS", "MS")),
    (("oil", "gas", "energy"), ("XOM", "CVX", "COP", "EOG", "SLB", "BP")),
    (("auto",), ("TM", "F", "GM", "HMC", "STLA")),
    (("consumer defensive", "household", "beverage", "packaged"), ("PG", "KO", "PEP", "COST", "WMT", "CL")),
    (("it services", "software & services"), ("TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS")),
    (("private sector bank", "public sector bank"), ("HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS")),
    (("refineries", "oil & gas"), ("RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS")),
]


def listing_suffix(ticker: str) -> str:
    parts = ticker.upper().split(".", 1)
    return f".{parts[1]}" if len(parts) == 2 else ""


def select_peers(ticker: str, industry: str | None, sector: str | None, overrides: list[str] | None) -> tuple[list[str], str]:
    target = ticker.upper()
    if overrides:
        cleaned = []
        for item in overrides:
            symbol = item.strip().upper()
            if symbol and symbol != target and symbol not in cleaned:
                cleaned.append(symbol)
        return cleaned[:6], "Peer group supplied by the user."

    text = f"{industry or ''} {sector or ''}".lower()
    suffix = listing_suffix(target)
    for keywords, universe in UNIVERSES:
        if any(keyword in text for keyword in keywords):
            same_listing = [item for item in universe if item != target and listing_suffix(item) == suffix]
            pool = same_listing or [item for item in universe if item != target]
            if suffix and not same_listing:
                return pool[:5], (
                    f"Matched the configured universe for '{keywords[0]}', but no same-listing peers were tagged. "
                    "Cross-listing peers are used and are a weaker comparison."
                )
            if pool:
                return pool[:5], f"Matched the configured educational universe for '{keywords[0]}'. Same-sector membership alone is not enough; the keyword list is narrower."
    return [], "No peer universe matched this industry, and no override was provided. Comparable valuation is omitted."


def multiple_set(
    *,
    ticker: str,
    name: str | None,
    price: float | None,
    market_cap: float | None,
    enterprise_value: float | None,
    revenue: float | None,
    net_income: float | None,
    equity: float | None,
    ebitda: float | None,
) -> PeerMultiple:
    shares = safe_div(market_cap, price)
    eps = safe_div(net_income, shares)
    pe = safe_div(price, eps) if eps is not None and eps > 0 else None
    ps = safe_div(market_cap, revenue) if revenue is not None and revenue > 0 else None
    pb = safe_div(market_cap, equity) if equity is not None and equity > 0 else None
    ev_ebitda = safe_div(enterprise_value, ebitda) if ebitda is not None and ebitda > 0 else None
    ev_revenue = safe_div(enterprise_value, revenue) if revenue is not None and revenue > 0 else None
    reason = None
    if all(value is None for value in (pe, ps, pb, ev_ebitda, ev_revenue)):
        reason = "No meaningful multiple could be calculated."
    return PeerMultiple(
        ticker=ticker,
        name=name,
        price_to_earnings=pe,
        price_to_sales=ps,
        price_to_book=pb,
        ev_to_ebitda=ev_ebitda,
        ev_to_revenue=ev_revenue,
        excluded_reason=reason,
    )


def _stats(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.median(values), statistics.fmean(values)


def summarize(peers: list[PeerMultiple]) -> tuple[dict[str, float | None], dict[str, float | None]]:
    usable = [peer for peer in peers if peer.excluded_reason is None]
    keys = ("price_to_earnings", "price_to_sales", "price_to_book", "ev_to_ebitda", "ev_to_revenue")
    medians: dict[str, float | None] = {}
    means: dict[str, float | None] = {}
    for key in keys:
        median, mean = _stats([getattr(peer, key) for peer in usable if getattr(peer, key) is not None])
        medians[key] = median
        means[key] = mean
    return medians, means


def implied_share_price(
    medians: dict[str, float | None],
    *,
    eps: float | None,
    revenue: float | None,
    shares: float | None,
    equity: float | None,
    ebitda: float | None,
    net_debt: float | None,
) -> tuple[float | None, list[str]]:
    """Apply median peer multiples to the target. Negative earnings and EBITDA are not used."""
    prices: list[float] = []
    notes: list[str] = []
    if medians.get("price_to_earnings") and eps and eps > 0:
        prices.append(medians["price_to_earnings"] * eps)
        notes.append("P/E × target EPS")
    if medians.get("price_to_sales") and revenue and shares and revenue > 0 and shares > 0:
        prices.append(medians["price_to_sales"] * revenue / shares)
        notes.append("P/S × revenue per share")
    if medians.get("price_to_book") and equity and shares and equity > 0 and shares > 0:
        prices.append(medians["price_to_book"] * equity / shares)
        notes.append("P/B × book value per share")
    if medians.get("ev_to_ebitda") and ebitda and ebitda > 0 and shares and shares > 0 and net_debt is not None:
        equity_value = medians["ev_to_ebitda"] * ebitda - net_debt
        price = safe_div(equity_value, shares)
        if price and price > 0:
            prices.append(price)
            notes.append("EV/EBITDA bridged with net debt")
    if medians.get("ev_to_revenue") and revenue and revenue > 0 and shares and shares > 0 and net_debt is not None:
        equity_value = medians["ev_to_revenue"] * revenue - net_debt
        price = safe_div(equity_value, shares)
        if price and price > 0:
            prices.append(price)
            notes.append("EV/revenue bridged with net debt")
    if not prices:
        return None, ["No peer multiple produced a per-share value."]
    return statistics.median(prices), notes


def peer_group_is_thin(count: int) -> bool:
    return count < VALUATION.min_peers
