"""Financial statements, ratios, and a rule-based health label."""

from __future__ import annotations

import asyncio

from app.domain.models import CompanySnapshot, HealthResult
from app.finance.health import classify_health


class FinancialDataAgent:
    async def run(self, snapshot: CompanySnapshot) -> HealthResult:
        await asyncio.sleep(0)
        return classify_health(snapshot.annual, snapshot.market.industry, snapshot.market.sector)


def empty_health(reason: str) -> HealthResult:
    return HealthResult(
        label="INSUFFICIENT_DATA",
        score=None,
        basis="general_heuristic",
        checks_passed=0,
        checks_evaluated=0,
        missing=[reason],
        evidence=[],
        history=[],
    )
