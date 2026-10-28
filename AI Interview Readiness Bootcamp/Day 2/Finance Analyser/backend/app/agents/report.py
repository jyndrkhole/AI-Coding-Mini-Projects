"""Synthesis only. Numbers and labels are copied from the specialist results."""

from __future__ import annotations

import json

from app.agents.disagreement import find_disagreement
from app.domain.models import (
    Assessment,
    DataQuality,
    Disagreement,
    HealthResult,
    MarketSnapshot,
    NewsResult,
    ReportSection,
    RiskResult,
    ValuationResult,
)
from app.finance.dcf import upside_percent
from app.llm import LLMClient


def _compact(value: float | None, currency: str | None) -> str:
    if value is None:
        return "unavailable"
    sign = "-" if value < 0 else ""
    amount = abs(value)
    prefix = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£"}.get((currency or "").upper(), f"{currency} " if currency else "")
    for unit, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if amount >= scale:
            return f"{sign}{prefix}{amount / scale:.2f}{unit}"
    return f"{sign}{prefix}{amount:,.0f}"


def _pct(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.1%}"


def _num(value: float | None, digits: int = 2) -> str:
    return "unavailable" if value is None else f"{value:.{digits}f}"


def _metric(health: HealthResult, key: str) -> float | None:
    for metric in health.metrics:
        if metric.key == key:
            return metric.value
    return None


def build_sections(
    market: MarketSnapshot,
    health: HealthResult,
    valuation: ValuationResult,
    risk: RiskResult,
    news: NewsResult,
    assessment: Assessment,
    quality: DataQuality,
    disagreement: Disagreement,
) -> list[ReportSection]:
    currency = market.currency
    price = _compact(market.price, currency) if market.price and market.price >= 1000 else (
        "unavailable" if market.price is None else f"{market.price:,.2f} {currency or ''}".strip()
    )
    intrinsic = "unavailable" if valuation.intrinsic_value_per_share is None else f"{valuation.intrinsic_value_per_share:,.2f}"
    upside = "unavailable" if valuation.upside_percent is None else f"{valuation.upside_percent:.1f}%"
    return [
        ReportSection(
            id="executive_summary",
            title="Executive Summary",
            paragraphs=[
                f"{market.company_name} ({market.ticker}) is rated {assessment.label.replace('_', ' ')} by the rating engine"
                + (f" with a score of {assessment.score:.2f} out of 5." if assessment.score is not None else "."),
                f"Financial health is {health.label}. Valuation is {valuation.label}. Risk is {risk.label}. News sentiment is {news.label}.",
                f"The value used for that valuation label is {intrinsic} per share against a market price of {price}, which is {upside}.",
                "News sentiment does not replace the financial or valuation result.",
            ],
        ),
        ReportSection(
            id="company_overview",
            title="Company Overview",
            paragraphs=[
                f"{market.company_name} trades as {market.ticker}"
                + (f" on {market.exchange}." if market.exchange else "."),
                f"Sector: {market.sector or 'unavailable'}. Industry: {market.industry or 'unavailable'}. Currency: {currency or 'unavailable'}.",
            ],
        ),
        ReportSection(
            id="market_snapshot",
            title="Current Market Snapshot",
            paragraphs=[
                f"Price: {price}. Previous close: {_compact(market.previous_close, currency)}. As of: {market.price_as_of or 'unavailable'}.",
                f"Market cap: {_compact(market.market_cap, currency)}. Enterprise value: {_compact(market.enterprise_value, currency)} ({market.enterprise_value_source or 'source unavailable'}).",
                f"Shares used: {_compact(market.shares, None)}. Source: {market.shares_source or 'unavailable'}. Beta: {_num(market.beta)}.",
            ],
        ),
        ReportSection(
            id="financial_health",
            title="Financial Health",
            paragraphs=[
                f"Label {health.label} on the {health.basis.replace('_', ' ')}. "
                + (
                    f"{health.checks_passed} of {health.checks_evaluated} applicable checks passed."
                    if health.score is not None
                    else "Not enough checks could be evaluated."
                )
            ],
            bullets=health.evidence,
        ),
        ReportSection(
            id="historical_performance",
            title="Historical Financial Performance",
            paragraphs=[
                "Annual figures below are the retrieved statements, not forecasts."
                if health.history
                else "No annual history was available."
            ],
            bullets=[
                f"{point.period}: revenue {_compact(point.revenue, currency)}, net income {_compact(point.net_income, currency)}, free cash flow {_compact(point.free_cash_flow, currency)}."
                for point in health.history
            ],
        ),
        ReportSection(
            id="income_statement",
            title="Income Statement Analysis",
            paragraphs=[
                f"Revenue growth {_pct(_metric(health, 'revenue_growth'))}. Gross margin {_pct(_metric(health, 'gross_margin'))}. "
                f"Operating margin {_pct(_metric(health, 'operating_margin'))}. Net margin {_pct(_metric(health, 'net_margin'))}. "
                f"EPS growth {_pct(_metric(health, 'eps_growth'))}."
            ],
        ),
        ReportSection(
            id="balance_sheet",
            title="Balance Sheet Analysis",
            paragraphs=[
                f"Net debt {_compact(_metric(health, 'net_debt'), currency)}. Working capital {_compact(_metric(health, 'working_capital'), currency)}. "
                f"Debt to equity {_num(_metric(health, 'debt_to_equity'))}. Current ratio {_num(_metric(health, 'current_ratio'))}."
            ],
            bullets=[metric.note for metric in health.metrics if metric.note and metric.key in {"debt_to_equity", "net_debt", "roe"}],
        ),
        ReportSection(
            id="cash_flow",
            title="Cash Flow Analysis",
            paragraphs=[
                f"Free cash flow margin {_pct(_metric(health, 'fcf_margin'))}. Free cash flow growth {_pct(_metric(health, 'fcf_growth'))}. "
                f"Operating cash flow / net income {_num(_metric(health, 'ocf_to_net_income'))}. "
                f"Dividend payout {_pct(_metric(health, 'dividend_payout'))}. Dividend coverage by free cash flow {_num(_metric(health, 'dividend_cash_coverage'))}."
            ],
        ),
        ReportSection(
            id="ratios",
            title="Key Financial Ratios",
            paragraphs=["Each ratio uses the formula stored with the metric. Missing inputs are left blank rather than filled in."],
            bullets=[_format_metric(metric, currency) for metric in health.metrics],
        ),
        ReportSection(
            id="dcf",
            title="DCF Valuation",
            paragraphs=[
                valuation.dcf.methodology,
                f"Status {valuation.dcf.status}. Model {valuation.dcf.model}. "
                f"Discount rate {_pct(valuation.dcf.discount_rate)}. Terminal growth {_pct(valuation.dcf.terminal_growth)}. "
                f"Enterprise value {_compact(valuation.dcf.enterprise_value, currency)}. Equity value {_compact(valuation.dcf.equity_value, currency)}. "
                f"DCF per share {_num(valuation.dcf.intrinsic_value_per_share)}. "
                f"Terminal value share {_pct(valuation.dcf.terminal_value_share)}.",
            ],
            bullets=valuation.dcf.limitations,
        ),
        ReportSection(
            id="peers",
            title="Comparable-Company Valuation",
            paragraphs=[
                valuation.peer_selection,
                f"Peer-implied price {_num(valuation.peer_implied_value)}. This median is an observation about the chosen group, not a fair-value claim.",
                f"Value used for the label: {valuation.method_used}",
            ],
            bullets=valuation.excluded_peers,
        ),
        ReportSection(
            id="scenarios",
            title="Bull, Base, and Bear Scenarios",
            paragraphs=["Scenarios shift growth, margin, the discount rate, and terminal growth around the base case. They are not management guidance."],
            bullets=[
                f"{scenario.name}: per share {_num(scenario.intrinsic_value_per_share)}, upside {_num(scenario.upside_percent, 1)}%. {scenario.note}"
                for scenario in valuation.scenarios
            ],
        ),
        ReportSection(
            id="risk",
            title="Risk Assessment",
            paragraphs=[f"Risk label {risk.label}. {risk.methodology}"],
            bullets=[f"[{flag.severity}] {flag.title}: {flag.evidence} {flag.impact}" for flag in risk.flags],
        ),
        ReportSection(
            id="news",
            title="Recent News and Sentiment",
            paragraphs=[
                f"Sentiment {news.label} by the {news.method} method over {news.lookback_days} days. "
                "This section is separate from the valuation label."
            ],
            bullets=[f"{article.published_at or 'undated'} — {article.title} ({article.sentiment})" for article in news.articles[:8]],
        ),
        ReportSection(
            id="strengths",
            title="Key Strengths",
            paragraphs=["Strengths are the health checks that passed."] if health.strengths else ["No health check passed, or none could be evaluated."],
            bullets=health.strengths,
        ),
        ReportSection(
            id="weaknesses",
            title="Key Weaknesses",
            paragraphs=["Weaknesses are the health checks that failed."] if health.weaknesses else ["No evaluated health check failed."],
            bullets=health.weaknesses,
        ),
        ReportSection(
            id="catalysts",
            title="Catalysts to Monitor",
            paragraphs=["These are items to watch. They are not predicted returns."],
            bullets=_catalysts(valuation, risk, news),
        ),
        ReportSection(
            id="assessment",
            title="Overall Investment Assessment",
            paragraphs=[
                assessment.methodology,
                f"Rating {assessment.label}. Confidence {assessment.confidence}.",
                "Component weights after any renormalization: "
                + ", ".join(
                    f"{component.name} {component.label} score {component.score if component.score is not None else 'missing'} weight {component.weight:.0%}"
                    for component in assessment.components
                )
                + ".",
            ],
            bullets=assessment.weight_notes,
        ),
        ReportSection(
            id="data_quality",
            title="Data Quality and Confidence",
            paragraphs=[
                f"Data confidence {quality.confidence}. Annual periods: {quality.years_annual}. Field coverage {quality.coverage_score:.0%}.",
                "Missing: " + (", ".join(quality.missing_fields) if quality.missing_fields else "none of the core fields."),
            ],
            bullets=quality.limitations,
        ),
        ReportSection(
            id="sources",
            title="Sources and Methodology",
            paragraphs=[
                "Prices and financial statements: Yahoo Finance via yfinance.",
                "Ratios, DCF, peer multiples, risk flags, and the rating are calculated in this application.",
                "Any paragraph marked as model commentary is an interpretation of those calculations. It is not a source of figures.",
                "This is educational decision support. It is not a solicitation, a forecast of returns, or an instruction to trade.",
            ],
            bullets=[f"{item.label}: {item.rationale} (source: {item.source}, value: {item.value})" for item in valuation.assumptions],
        ),
    ]


def _format_metric(metric, currency: str | None) -> str:
    if metric.value is None:
        shown = "unavailable"
    elif metric.unit == "percent":
        shown = _pct(metric.value)
    elif metric.unit == "currency":
        shown = _compact(metric.value, currency)
    else:
        shown = _num(metric.value)
    note = f" {metric.note}" if metric.note else ""
    usable = "" if metric.interpretable else " Not interpretable on its own."
    return f"{metric.label}: {shown} ({metric.formula}).{note}{usable}"


def _catalysts(valuation: ValuationResult, risk: RiskResult, news: NewsResult) -> list[str]:
    items = []
    if valuation.dcf.terminal_value_share and valuation.dcf.terminal_value_share > 0.7:
        items.append("Whether the discount rate or terminal-growth assumption still looks reasonable after the next results.")
    if any(flag.category == "financial" and flag.severity == "high" for flag in risk.flags):
        items.append("The next balance sheet: leverage, equity, and interest coverage.")
    if news.catalysts_negative:
        items.append("Follow-up on the negative headline: " + news.catalysts_negative[0])
    if news.catalysts_positive:
        items.append("Whether the positive headline shows up in revenue, margin, or cash flow.")
    if not items:
        items.append("The next annual or quarterly statements, compared with the margins and cash flow used here.")
    return items


def render_markdown(market: MarketSnapshot, sections: list[ReportSection], disagreement: Disagreement) -> str:
    lines = [f"# {market.company_name} ({market.ticker})", ""]
    if disagreement.consistent:
        lines.append("The specialist labels do not contain a configured conflict. They are still reported separately.")
    else:
        lines.append("## Where the agents disagree")
        lines.extend(f"- {item}" for item in disagreement.conflicts)
    lines.append("")
    for section in sections:
        lines.append(f"## {section.title}")
        lines.extend(section.paragraphs)
        lines.extend(f"- {bullet}" for bullet in section.bullets if bullet)
        if section.interpretation:
            lines.append(f"Model commentary ({section.interpretation_source}): {section.interpretation}")
        lines.append("")
    return "\n".join(lines)


class ReportWriter:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def write(self, market, health, valuation, risk, news, assessment, quality) -> tuple[list[ReportSection], str, Disagreement]:
        disagreement = find_disagreement(health.label, valuation.label, risk.label, news.label)
        sections = build_sections(market, health, valuation, risk, news, assessment, quality, disagreement)
        if self.llm.configured:
            await self._comment(sections, disagreement, assessment)
        return sections, render_markdown(market, sections, disagreement), disagreement

    async def _comment(self, sections: list[ReportSection], disagreement: Disagreement, assessment: Assessment) -> None:
        system = (
            "You comment on a finished equity brief. Return JSON with string keys "
            "executive_summary, strengths, weaknesses, risk, news, disagreement. "
            "Do not invent financial figures. Do not change or propose the rating. "
            "The rating is already decided and you must not restate a different one. "
            "If the payload says a figure is unavailable, leave it unavailable."
        )
        payload = {
            "rating": assessment.label,
            "conflicts": disagreement.conflicts,
            "sections": {section.id: {"paragraphs": section.paragraphs, "bullets": section.bullets[:6]} for section in sections},
        }
        parsed = await self.llm.complete_json(system, json.dumps(payload)[:12000])
        if not parsed:
            return
        allowed = {"executive_summary", "strengths", "weaknesses", "risk", "news", "disagreement"}
        for section in sections:
            text = parsed.get(section.id)
            if section.id in allowed and isinstance(text, str) and text.strip():
                section.interpretation = text.strip()
                section.interpretation_source = "llm"


def validate_report(report) -> None:
    """Reject a report whose labels or upside do not match the engines that produced them."""
    problems = []
    if report.disagreement.financial_health != report.health.label:
        problems.append("health label was rewritten")
    if report.disagreement.valuation != report.valuation.label:
        problems.append("valuation label was rewritten")
    if report.disagreement.risk != report.risk.label:
        problems.append("risk label was rewritten")
    if report.disagreement.news != report.news.label:
        problems.append("news label was rewritten")
    expected = upside_percent(report.valuation.intrinsic_value_per_share, report.market.price)
    actual = report.valuation.upside_percent
    if expected is None and actual is not None:
        problems.append("upside was produced without a price or value")
    if expected is not None and actual is not None and abs(expected - actual) > 0.05:
        problems.append("upside does not match intrinsic value and price")
    titles = [section.title for section in report.sections]
    required = [
        "Executive Summary",
        "Company Overview",
        "Current Market Snapshot",
        "Financial Health",
        "Historical Financial Performance",
        "Income Statement Analysis",
        "Balance Sheet Analysis",
        "Cash Flow Analysis",
        "Key Financial Ratios",
        "DCF Valuation",
        "Comparable-Company Valuation",
        "Bull, Base, and Bear Scenarios",
        "Risk Assessment",
        "Recent News and Sentiment",
        "Key Strengths",
        "Key Weaknesses",
        "Catalysts to Monitor",
        "Overall Investment Assessment",
        "Data Quality and Confidence",
        "Sources and Methodology",
    ]
    if titles != required:
        problems.append("report sections are missing or out of order")
    if problems:
        raise RuntimeError("Report validation failed: " + "; ".join(problems))
