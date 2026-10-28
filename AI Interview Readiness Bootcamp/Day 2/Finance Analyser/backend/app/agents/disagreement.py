"""Keep specialist labels side by side when they point in different directions."""

from __future__ import annotations

from app.domain.models import Disagreement, HealthLabel, RiskLabel, SentimentLabel, ValuationLabel

BULLISH = {"BULLISH", "STRONGLY_BULLISH"}
BEARISH = {"BEARISH", "STRONGLY_BEARISH"}
UNDER = {"SLIGHTLY_UNDERVALUED", "SIGNIFICANTLY_UNDERVALUED"}
OVER = {"SLIGHTLY_OVERVALUED", "SIGNIFICANTLY_OVERVALUED"}


def find_disagreement(
    health: HealthLabel,
    valuation: ValuationLabel,
    risk: RiskLabel,
    news: SentimentLabel,
) -> Disagreement:
    conflicts: list[str] = []
    if valuation in OVER and news in BULLISH:
        conflicts.append(
            f"Valuation is {valuation.replace('_', ' ').lower()} while news sentiment is {news.replace('_', ' ').lower()}. "
            "Bullish headlines are not treated as evidence that the shares are inexpensive."
        )
    if valuation in UNDER and news in BEARISH:
        conflicts.append(
            "The valuation screen is inexpensive while the news tone is bearish. A low multiple is not recorded as a positive catalyst."
        )
    if health in {"WEAK", "MIXED"} and news in BULLISH:
        conflicts.append(
            f"Financial health is {health.lower()} and news sentiment is constructive. Headlines do not change the statement score."
        )
    if health == "STRONG" and valuation in OVER:
        conflicts.append("Financial health is strong and the valuation is rich. Business quality and the price paid are separate conclusions.")
    if risk in {"HIGH", "ELEVATED"} and valuation in UNDER:
        conflicts.append(
            f"Risk is {risk.lower()} while the valuation screen shows a discount. The discount may be compensation for the flagged risks."
        )
    if health == "STRONG" and risk in {"HIGH", "ELEVATED"}:
        conflicts.append("The health rules and the risk flags do not agree. Both labels are preserved.")
    return Disagreement(
        financial_health=health,
        valuation=valuation,
        risk=risk,
        news=news,
        conflicts=conflicts,
        consistent=not conflicts,
    )
