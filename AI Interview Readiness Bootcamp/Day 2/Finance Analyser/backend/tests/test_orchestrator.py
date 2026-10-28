"""The orchestrator must actually overlap independent agents."""

from __future__ import annotations

import asyncio

from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.domain.models import AnalyzeRequest, CompanySnapshot, MarketSnapshot, NewsArticle
from app.llm import LLMClient
from tests.test_engines import period


class MemoryStore:
    def __init__(self) -> None:
        self.saved = []

    def save(self, report) -> None:
        self.saved.append(report)


class FakeProvider:
    def __init__(self, snapshot: CompanySnapshot) -> None:
        self.snapshot = snapshot

    async def get_snapshot(self, ticker: str) -> CompanySnapshot:
        await asyncio.sleep(0.02)
        market = self.snapshot.market.model_copy(update={"ticker": ticker})
        return self.snapshot.model_copy(update={"market": market})

    async def get_news(self, ticker: str, lookback_days: int) -> list[NewsArticle]:
        await asyncio.sleep(0.02)
        return [NewsArticle(id="n1", title=f"{ticker} beats estimates", summary="Profit rose")]


def _snapshot() -> CompanySnapshot:
    return CompanySnapshot(
        market=MarketSnapshot(
            ticker="TEST",
            company_name="Test Widgets",
            exchange="NYSE",
            sector="Widgets",
            industry="Specialty widgets",
            currency="USD",
            price=50,
            market_cap=5000,
            shares=100,
            shares_source="test",
            beta=1.0,
            enterprise_value=5020,
            enterprise_value_source="test",
        ),
        annual=[period(2022, revenue=800), period(2023, revenue=900), period(2024)],
    )


def test_parallel_agents_and_saved_report():
    settings = Settings(llm_provider="", agent_timeout_seconds=10)
    llm = LLMClient(settings)
    store = MemoryStore()
    orchestrator = Orchestrator(FakeProvider(_snapshot()), llm, store, settings)

    async def slow(delay, original):
        async def run(*args, **kwargs):
            await asyncio.sleep(delay)
            return await original(*args, **kwargs)

        return run

    async def scenario():
        orchestrator.financial.run = await slow(0.05, orchestrator.financial.run)
        orchestrator.news.run = await slow(0.25, orchestrator.news.run)
        orchestrator.risk.run = await slow(0.05, orchestrator.risk.run)
        return await orchestrator.analyze(AnalyzeRequest(ticker="test"))

    report = asyncio.run(scenario())
    spans = {span.name: span for span in report.trace}

    def ends(name: str) -> float:
        span = spans[name]
        return span.started_offset_ms + span.duration_ms

    assert spans["FinancialDataAgent"].started_offset_ms < ends("NewsAndSentimentAgent")
    assert spans["NewsAndSentimentAgent"].started_offset_ms < ends("FinancialDataAgent")
    assert spans["RiskAgent"].started_offset_ms < ends("FinancialDataAgent")
    assert spans["ValuationAgent"].started_offset_ms + 20 < ends("NewsAndSentimentAgent")
    assert spans["ReportWriterAgent"].started_offset_ms + 15 >= ends("NewsAndSentimentAgent")
    assert spans["ReportWriterAgent"].started_offset_ms + 15 >= ends("ValuationAgent")
    assert spans["ReportWriterAgent"].started_offset_ms + 15 >= ends("RiskAgent")
    assert len(report.sections) == 20
    assert report.llm.used is False
    assert "Educational research" in report.disclaimer
    assert store.saved[0].id == report.id
    assert report.health.label == "STRONG"
