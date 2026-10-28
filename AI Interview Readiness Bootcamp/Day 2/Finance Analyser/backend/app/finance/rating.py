"""Deterministic rating. Missing critical inputs stay missing; they are not scored as neutral."""

from __future__ import annotations

from app.domain.models import Assessment, ComponentScore, DataQuality
from app.finance.thresholds import (
    HEALTH_SCORES,
    RATING,
    RISK_SCORES,
    SENTIMENT_SCORES,
    VALUATION_SCORES,
)


def rate(
    health: str,
    valuation: str,
    risk: str,
    news: str,
    quality: DataQuality,
) -> Assessment:
    raw = [
        ("Financial health", health, HEALTH_SCORES.get(health), RATING.financial_health, True),
        ("Valuation", valuation, VALUATION_SCORES.get(valuation), RATING.valuation, True),
        ("Risk", risk, RISK_SCORES.get(risk), RATING.risk, False),
        ("News and sentiment", news, SENTIMENT_SCORES.get(news), RATING.news, False),
    ]
    notes: list[str] = []
    missing_critical = [name for name, _label, score, _weight, critical in raw if critical and score is None]
    if missing_critical or quality.confidence == "INSUFFICIENT":
        if quality.confidence == "INSUFFICIENT":
            notes.append("Statement or price coverage is insufficient, so no rating is issued.")
        if missing_critical:
            notes.append("Critical components without a score: " + ", ".join(missing_critical) + ". They were not filled with a neutral score.")
        components = [
            ComponentScore(name=name, label=label, score=score, weight=weight, critical=critical)
            for name, label, score, weight, critical in raw
        ]
        return Assessment(
            label="INSUFFICIENT_DATA",
            score=None,
            confidence="INSUFFICIENT",
            components=components,
            weight_notes=notes,
            methodology=_methodology(),
        )

    available = [(name, label, score, weight, critical) for name, label, score, weight, critical in raw if score is not None]
    dropped = [name for name, _label, score, _weight, _critical in raw if score is None]
    weight_sum = sum(weight for _n, _l, _s, weight, _c in available)
    components = []
    total = 0.0
    for name, label, score, weight, critical in raw:
        used = 0.0 if score is None else weight / weight_sum
        if score is not None:
            total += score * used
        components.append(ComponentScore(name=name, label=label, score=score, weight=used, critical=critical))
    if dropped:
        notes.append(
            "Weights were renormalized after dropping "
            + ", ".join(dropped)
            + ". Confidence is reduced because those components were not treated as neutral."
        )

    if total >= RATING.strong_buy:
        label = "STRONG_BUY"
    elif total >= RATING.buy:
        label = "BUY"
    elif total >= RATING.hold:
        label = "HOLD"
    elif total >= RATING.sell:
        label = "SELL"
    else:
        label = "STRONG_SELL"

    confidence = quality.confidence
    if dropped:
        confidence = "LOW" if confidence == "LOW" or len(dropped) > 1 else "MEDIUM"
    if quality.years_annual < 3 and confidence == "HIGH":
        confidence = "MEDIUM"
        notes.append("Fewer than three annual periods are available, so confidence is capped at MEDIUM.")
    return Assessment(
        label=label,  # type: ignore[arg-type]
        score=total,
        confidence=confidence,  # type: ignore[arg-type]
        components=components,
        weight_notes=notes,
        methodology=_methodology(),
    )


def _methodology() -> str:
    return (
        f"Score = 5×financial health weight ({RATING.financial_health:.0%}) "
        f"+ 5-point valuation weight ({RATING.valuation:.0%}) "
        f"+ risk weight ({RATING.risk:.0%}) "
        f"+ news weight ({RATING.news:.0%}), after dropping missing non-critical components and renormalizing. "
        f"Thresholds: STRONG_BUY ≥ {RATING.strong_buy}, BUY ≥ {RATING.buy}, HOLD ≥ {RATING.hold}, "
        f"SELL ≥ {RATING.sell}, otherwise STRONG_SELL. "
        "News cannot replace a missing valuation or health score."
    )
