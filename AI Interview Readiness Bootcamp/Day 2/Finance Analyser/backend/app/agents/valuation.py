"""Valuation specialist. The math is in finance.valuation; this agent only gathers peers."""

from __future__ import annotations

import asyncio

from app.domain.models import AssumptionOverrides, CompanySnapshot, PeerMultiple, ValuationResult
from app.finance.peers import multiple_set
from app.finance.valuation import assemble_valuation


class ValuationAgent:
    async def run(
        self,
        snapshot: CompanySnapshot,
        peer_results: list[tuple[str, CompanySnapshot | Exception]],
        selection: str,
        overrides: AssumptionOverrides | None,
    ) -> ValuationResult:
        await asyncio.sleep(0)
        rows: list[PeerMultiple] = []
        for symbol, result in peer_results:
            if isinstance(result, Exception):
                rows.append(PeerMultiple(ticker=symbol, excluded_reason=f"Peer data failed: {result}"))
                continue
            latest = result.annual[-1] if result.annual else None
            if latest is None:
                rows.append(PeerMultiple(ticker=symbol, name=result.market.company_name, excluded_reason="No annual statements."))
                continue
            rows.append(
                multiple_set(
                    ticker=symbol,
                    name=result.market.company_name,
                    price=result.market.price,
                    market_cap=result.market.market_cap,
                    enterprise_value=result.market.enterprise_value,
                    revenue=latest.revenue,
                    net_income=latest.net_income,
                    equity=latest.equity,
                    ebitda=latest.ebitda,
                )
            )
        return assemble_valuation(snapshot.annual, snapshot.market, rows, selection, overrides)
