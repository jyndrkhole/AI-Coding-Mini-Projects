"""Supervisor. Phase 2 agents overlap; valuation waits for the statements; the writer goes last."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from app.agents.financial import FinancialDataAgent, empty_health
from app.agents.news import NewsAgent, empty_news
from app.agents.report import ReportWriter, validate_report
from app.agents.risk import RiskAgent, empty_risk
from app.agents.valuation import ValuationAgent
from app.config import Settings
from app.data.errors import ProviderError, TickerNotFound
from app.domain.models import AnalysisReport, AnalyzeRequest, LLMInfo, TraceSpan
from app.finance.peers import select_peers
from app.finance.quality import assess_quality
from app.finance.rating import rate
from app.llm import LLMClient

log = logging.getLogger(__name__)
DISCLAIMER = (
    "Educational research and decision support. Not a recommendation to buy or sell, "
    "and not a guarantee of investment returns. Figures are only those retrieved or calculated; gaps stay visible."
)


class Orchestrator:
    def __init__(self, provider, llm: LLMClient, store, settings: Settings) -> None:
        self.provider = provider
        self.llm = llm
        self.store = store
        self.settings = settings
        self.financial = FinancialDataAgent()
        self.news = NewsAgent(llm)
        self.risk = RiskAgent()
        self.valuation = ValuationAgent()
        self.writer = ReportWriter(llm)

    async def analyze(self, request: AnalyzeRequest, on_event=None) -> AnalysisReport:
        started = time.perf_counter()
        trace: list[TraceSpan] = []

        async def emit(payload: dict) -> None:
            if on_event is not None:
                await on_event(payload)

        async def span(name: str, phase: str, coro):
            await emit({"type": "span", "name": name, "phase": phase, "event": "start"})
            began = time.perf_counter()
            try:
                result = await asyncio.wait_for(coro, timeout=self.settings.agent_timeout_seconds)
            finally:
                duration_ms = (time.perf_counter() - began) * 1000
                trace.append(
                    TraceSpan(
                        name=name,
                        phase=phase,
                        started_offset_ms=(began - started) * 1000,
                        duration_ms=duration_ms,
                    )
                )
                await emit({"type": "span", "name": name, "phase": phase, "event": "end", "duration_ms": duration_ms})
            return result

        ticker = request.ticker.strip().upper()
        await emit({"type": "phase", "phase": "data"})
        try:
            snapshot, articles = await asyncio.gather(
                span("MarketData", "data", self.provider.get_snapshot(ticker)),
                span("NewsFetch", "data", self.provider.get_news(ticker, request.news_lookback_days)),
            )
        except (TickerNotFound, ProviderError):
            raise
        except Exception as exc:
            raise ProviderError(f"Market data failed for {ticker}: {exc}") from exc

        await emit({"type": "phase", "phase": "specialists"})

        async def specialist(name, phase, coro, fallback):
            try:
                return await span(name, phase, coro)
            except Exception as exc:
                log.warning("%s failed: %s", name, type(exc).__name__)
                return fallback()

        async with asyncio.TaskGroup() as group:
            health_task = group.create_task(
                specialist("FinancialDataAgent", "specialists", self.financial.run(snapshot), lambda: empty_health("The financial agent failed."))
            )
            news_task = group.create_task(
                specialist(
                    "NewsAndSentimentAgent",
                    "specialists",
                    self.news.run(articles, snapshot, request.news_lookback_days),
                    lambda: empty_news(request.news_lookback_days, "The news agent failed."),
                )
            )
            risk_task = group.create_task(
                specialist("RiskAgent", "specialists", self.risk.run(snapshot, articles), lambda: empty_risk("The risk agent failed."))
            )
            health = await health_task
            await emit({"type": "phase", "phase": "valuation"})
            symbols, selection = select_peers(ticker, snapshot.market.industry, snapshot.market.sector, request.peers)

            async def load_peer(symbol: str):
                try:
                    return symbol, await self.provider.get_snapshot(symbol)
                except Exception as exc:
                    return symbol, exc

            peer_results = await span(
                "PeerFetch",
                "valuation",
                asyncio.gather(*(load_peer(symbol) for symbol in symbols)) if symbols else _empty_peers(),
            )
            try:
                valuation = await span(
                    "ValuationAgent",
                    "valuation",
                    self.valuation.run(snapshot, list(peer_results), selection, request.assumptions),
                )
            except Exception as exc:
                log.warning("ValuationAgent failed: %s", type(exc).__name__)
                from app.finance.valuation import assemble_valuation

                valuation = assemble_valuation(
                    snapshot.annual,
                    snapshot.market,
                    [],
                    f"Valuation agent failed: {exc}",
                    request.assumptions,
                )
            news = await news_task
            risk_result = await risk_task

        risk = self.risk.add_valuation(risk_result, valuation)
        quality = assess_quality(snapshot)
        assessment = rate(health.label, valuation.label, risk.label, news.label, quality)
        await emit({"type": "phase", "phase": "report"})
        sections, markdown, disagreement = await span(
            "ReportWriterAgent",
            "report",
            self.writer.write(snapshot.market, health, valuation, risk, news, assessment, quality),
        )
        report = AnalysisReport(
            id=uuid.uuid4().hex,
            ticker=snapshot.market.ticker,
            company_name=snapshot.market.company_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            currency=snapshot.market.currency,
            rating=assessment,
            disagreement=disagreement,
            market=snapshot.market,
            health=health,
            valuation=valuation,
            risk=risk,
            news=news,
            data_quality=quality,
            assumptions=valuation.assumptions,
            sections=sections,
            brief_markdown=markdown,
            trace=trace,
            llm=LLMInfo(
                provider=self.llm.provider,
                model=self.llm.model,
                used=self.llm.configured,
                message=self.llm.message,
            ),
            disclaimer=DISCLAIMER,
        )
        validate_report(report)
        if self.store is not None:
            await asyncio.to_thread(self.store.save, report)
        await emit({"type": "done"})
        return report


async def _empty_peers():
    return []
