"""Deterministic engines: ratios, DCF, health, rating, peers, and news labels."""

from __future__ import annotations

import pandas as pd

from app.agents.disagreement import find_disagreement
from app.agents.news import label_from_score, lexicon_score, overall_label, prepare_articles
from app.data.normalize import frames_to_periods
from app.domain.models import CompanySnapshot, MarketSnapshot, NewsArticle, PeriodFinancials
from app.finance.dcf import build_dcf, present_value, project_fcff, upside_percent
from app.finance.health import classify_health
from app.finance.peers import multiple_set, select_peers
from app.finance.quality import assess_quality
from app.finance.rating import rate
from app.finance.ratios import build_metrics
from app.finance.valuation import assemble_valuation, classify_upside


def period(year: int, **overrides) -> PeriodFinancials:
    data = dict(
        period_end=f"{year}-12-31",
        period_type="annual",
        revenue=1000.0,
        gross_profit=400.0,
        operating_income=200.0,
        ebit=200.0,
        ebitda=230.0,
        net_income=150.0,
        interest_expense=10.0,
        tax_provision=40.0,
        pretax_income=190.0,
        eps=1.5,
        depreciation=30.0,
        cash=100.0,
        total_assets=800.0,
        current_assets=300.0,
        inventory=50.0,
        total_liabilities=400.0,
        current_liabilities=150.0,
        total_debt=120.0,
        equity=400.0,
        shares=100.0,
        operating_cash_flow=180.0,
        capex=40.0,
        free_cash_flow=140.0,
        dividends=20.0,
    )
    data.update(overrides)
    return PeriodFinancials(**data)


def test_fcff_formula_and_present_value():
    flows = project_fcff(1000, [0.0], 0.20, 0.25, 0.03, 0.04, 0.10)
    assert flows == [140]
    total, terminal, _pv_terminal, years = present_value([110], 0.10, 0.02)
    assert terminal == 110 * 1.02 / 0.08
    assert total == (110 + terminal) / 1.10
    assert abs(years[0].present_value - 100) < 1e-9


def test_dcf_rejects_terminal_growth_at_or_above_discount_rate():
    result = build_dcf(
        [period(2024)],
        shares=10,
        net_debt=0,
        discount_rate=0.04,
        discount_source="test",
        terminal_growth=0.04,
        growth_rates=[0.02],
        ebit_margin=0.2,
        tax_rate=0.25,
        da_pct=0.03,
        capex_pct=0.04,
        nwc_pct=0.1,
        model="fcff_wacc",
    )
    assert result.status == "unavailable"
    assert result.sensitivity == []


def test_sensitivity_skips_invalid_pairs():
    result = build_dcf(
        [period(2024)],
        shares=10,
        net_debt=0,
        discount_rate=0.08,
        discount_source="test",
        terminal_growth=0.02,
        growth_rates=[0.0],
        ebit_margin=0.2,
        tax_rate=0.25,
        da_pct=0.03,
        capex_pct=0.04,
        nwc_pct=0.1,
        model="fcff_wacc",
    )
    assert result.status == "ok"
    assert all(cell.terminal_growth < cell.discount_rate for cell in result.sensitivity)
    assert result.intrinsic_value_per_share is not None


def test_upside_guards_missing_or_zero_price():
    assert upside_percent(100, None) is None
    assert upside_percent(100, 0) is None
    assert upside_percent(None, 50) is None
    assert upside_percent(150, 100) == 50


def test_negative_equity_is_not_low_leverage():
    metrics = build_metrics([period(2024, equity=-50, total_debt=100)])
    debt = next(metric for metric in metrics if metric.key == "debt_to_equity")
    assert debt.value is not None and debt.value < 0
    assert debt.interpretable is False
    assert "not low leverage" in (debt.note or "").lower() or "not low" in (debt.note or "").lower()
    health = classify_health([period(2023), period(2024, equity=-50, total_debt=100)])
    assert any("negative equity" in item.lower() for item in health.weaknesses)


def test_zero_denominator_is_missing_not_invented():
    metrics = build_metrics([period(2024, revenue=0, current_liabilities=0, equity=0)])
    by_key = {metric.key: metric for metric in metrics}
    assert by_key["gross_margin"].value is None
    assert by_key["current_ratio"].value is None
    assert by_key["debt_to_equity"].interpretable is False


def test_health_strong_company_and_insufficient_history():
    health = classify_health([period(2023, revenue=900, net_income=120), period(2024)], industry="Software")
    assert health.label == "STRONG"
    assert health.basis == "general_heuristic"
    assert classify_health([]).label == "INSUFFICIENT_DATA"


def test_bank_skips_current_ratio_penalty():
    health = classify_health(
        [period(2023, revenue=900), period(2024, current_assets=10, current_liabilities=100)],
        industry="Banks—Regional",
    )
    assert not any("current ratio is 0.10" in item.lower() for item in health.weaknesses)


def test_valuation_thresholds_and_blend_does_not_invent_peers():
    assert classify_upside(30) == "SLIGHTLY_UNDERVALUED"
    assert classify_upside(30.1) == "SIGNIFICANTLY_UNDERVALUED"
    assert classify_upside(10) == "FAIRLY_VALUED"
    assert classify_upside(-10) == "FAIRLY_VALUED"
    assert classify_upside(-30) == "SLIGHTLY_OVERVALUED"
    assert classify_upside(-30.1) == "SIGNIFICANTLY_OVERVALUED"
    assert classify_upside(None) == "INSUFFICIENT_DATA"
    market = MarketSnapshot(ticker="TEST", company_name="Test", currency="USD", price=10, market_cap=1000, shares=100, beta=1)
    valuation = assemble_valuation([period(2023, revenue=900), period(2024)], market, [], "No peers supplied.")
    assert valuation.peer_implied_value is None
    assert valuation.label != "INSUFFICIENT_DATA"
    assert valuation.dcf.model == "fcff_wacc"


def test_negative_free_cash_flow_does_not_silently_grow():
    annual = [period(2024, free_cash_flow=-20, capex=None, depreciation=None, current_assets=None)]
    market = MarketSnapshot(ticker="NEG", company_name="Neg", currency="EUR", price=8, shares=10, beta=1, market_cap=80)
    valuation = assemble_valuation(annual, market, [], "none")
    assert valuation.dcf.model in {"fcfe_cost_of_equity", "none"}
    assert valuation.dcf.status in {"unavailable", "unreliable"}
    assert valuation.label == "INSUFFICIENT_DATA"


def test_rating_keeps_disagreement_and_refuses_missing_valuation():
    quality = assess_quality(
        CompanySnapshot(
            market=MarketSnapshot(ticker="T", company_name="T", price=10, currency="USD"),
            annual=[period(2022), period(2023), period(2024)],
        )
    )
    bullish_but_expensive = rate("STRONG", "SIGNIFICANTLY_OVERVALUED", "HIGH", "BULLISH", quality)
    assert bullish_but_expensive.label in {"SELL", "STRONG_SELL"}
    assert bullish_but_expensive.components[3].label == "BULLISH"
    missing = rate("STRONG", "INSUFFICIENT_DATA", "LOW", "BULLISH", quality)
    assert missing.label == "INSUFFICIENT_DATA"
    assert missing.score is None
    dropped_news = rate("STRONG", "FAIRLY_VALUED", "LOW", "INSUFFICIENT_DATA", quality)
    assert dropped_news.label != "INSUFFICIENT_DATA"
    assert any("renormalized" in note.lower() for note in dropped_news.weight_notes)
    conflict = find_disagreement("STRONG", "SIGNIFICANTLY_OVERVALUED", "ELEVATED", "BULLISH")
    assert conflict.consistent is False
    assert conflict.valuation == "SIGNIFICANTLY_OVERVALUED"
    assert conflict.news == "BULLISH"


def test_peer_selection_is_not_the_whole_sector():
    peers, reason = select_peers("NVDA", "Semiconductors", "Technology", None)
    assert "NVDA" not in peers
    assert "AAPL" not in peers
    assert "AVGO" in peers
    assert "semiconductor" in reason.lower()
    apple, _ = select_peers("AAPL", "Consumer Electronics", "Technology", None)
    assert "SONY" in apple and "MSFT" not in apple
    empty, note = select_peers("ZZZZ", "Specialty widgets", None, None)
    assert empty == []
    assert "no peer universe" in note.lower()
    overridden, _ = select_peers("AAPL", "Software", "Technology", ["msft", "aapl", "orcl"])
    assert overridden == ["MSFT", "ORCL"]


def test_peer_multiples_skip_negative_earnings():
    row = multiple_set(
        ticker="X",
        name="X",
        price=10,
        market_cap=100,
        enterprise_value=120,
        revenue=50,
        net_income=-5,
        equity=40,
        ebitda=-2,
    )
    assert row.price_to_earnings is None
    assert row.ev_to_ebitda is None
    assert row.price_to_sales == 2


def test_statement_normalizer_uses_aliases_and_signs():
    income = pd.DataFrame(
        {"2024-12-31": [1000, 200, 150], "2023-12-31": [800, 160, 100]},
        index=["Total Revenue", "Operating Income", "Net Income"],
    )
    income.columns = pd.to_datetime(income.columns)
    balance = pd.DataFrame(
        {"2024-12-31": [80, 500, 200], "2023-12-31": [70, 450, 180]},
        index=["Cash And Cash Equivalents", "Total Assets", "Stockholders Equity"],
    )
    balance.columns = pd.to_datetime(balance.columns)
    cashflow = pd.DataFrame(
        {"2024-12-31": [180, -40, -10], "2023-12-31": [140, -30, -8]},
        index=["Operating Cash Flow", "Capital Expenditure", "Common Stock Dividend Paid"],
    )
    cashflow.columns = pd.to_datetime(cashflow.columns)
    periods = frames_to_periods(income, balance, cashflow, "annual", 5)
    assert [item.period_end for item in periods] == ["2023-12-31", "2024-12-31"]
    assert periods[-1].revenue == 1000
    assert periods[-1].capex == 40
    assert periods[-1].free_cash_flow == 140
    assert periods[-1].dividends == 10


def test_news_lexicon_does_not_invent_articles():
    assert lexicon_score("Company beats estimates and raises guidance") >= 2
    assert lexicon_score("Regulator opens a probe and lawsuit") <= -2
    assert label_from_score(0) == "NEUTRAL"
    snapshot = CompanySnapshot(
        market=MarketSnapshot(ticker="AAPL", company_name="Apple Inc.", price=100),
        annual=[period(2024)],
    )
    articles = prepare_articles(
        [NewsArticle(id="1", title="Apple beats estimates", summary="Profit rose")],
        snapshot,
    )
    assert articles[0].mentions_company is True
    assert overall_label(articles) in {"BULLISH", "STRONGLY_BULLISH"}
    assert overall_label([]) == "INSUFFICIENT_DATA"
