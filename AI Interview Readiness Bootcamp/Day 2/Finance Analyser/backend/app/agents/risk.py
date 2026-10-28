"""Risk flags from statements and, after valuation exists, from the DCF."""

from __future__ import annotations

import asyncio

from app.agents.news import prepare_articles
from app.domain.models import CompanySnapshot, NewsArticle, RiskResult, ValuationResult
from app.finance.risk_rules import classify_risk, financial_and_business_flags, news_flags, valuation_flags


class RiskAgent:
    async def run(self, snapshot: CompanySnapshot, articles: list[NewsArticle]) -> RiskResult:
        await asyncio.sleep(0)
        flags, evaluated, limitations = financial_and_business_flags(
            snapshot.annual,
            snapshot.market.industry,
            snapshot.market.sector,
        )
        if articles:
            news = prepare_articles(articles, snapshot)
            from app.domain.models import NewsResult

            provisional = NewsResult(label="NEUTRAL", lookback_days=0, method="lexicon", confidence="LOW", articles=news)
            flags.extend(news_flags(provisional))
            evaluated += 1
        else:
            limitations.append("No articles were available, so event risk was not scored.")
        limitations.append("Customer and supplier concentration are not asserted; those disclosures were not retrieved.")
        return classify_risk(flags, evaluated, limitations)

    def add_valuation(self, risk: RiskResult, valuation: ValuationResult) -> RiskResult:
        extra = 0
        if valuation.dcf.status != "unavailable":
            extra += 1
        if valuation.upside_percent is not None:
            extra += 1
        return classify_risk(
            risk.flags + valuation_flags(valuation),
            risk.evaluated_signals + extra,
            risk.limitations,
        )


def empty_risk(reason: str) -> RiskResult:
    return classify_risk([], 0, [reason])
