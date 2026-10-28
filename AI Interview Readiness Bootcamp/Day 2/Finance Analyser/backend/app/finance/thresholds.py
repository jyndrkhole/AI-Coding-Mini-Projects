"""Central, configurable heuristics. These are application rules, not market standards."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthThresholds:
    min_checks: int = 5
    financial_company_min_checks: int = 4
    strong: float = 0.80
    solid: float = 0.65
    mixed: float = 0.45
    operating_margin: float = 0.08
    net_margin: float = 0.05
    roe: float = 0.10
    roa: float = 0.04
    current_ratio: float = 1.2
    debt_to_equity: float = 1.5
    interest_coverage: float = 3.0
    ocf_to_net_income: float = 0.8


@dataclass(frozen=True)
class ValuationThresholds:
    significant_upside: float = 30.0
    slight_upside: float = 10.0
    slight_downside: float = -10.0
    significant_downside: float = -30.0
    dcf_weight: float = 0.60
    peer_weight: float = 0.40
    min_peers: int = 3


@dataclass(frozen=True)
class RiskThresholds:
    debt_to_equity_high: float = 2.0
    debt_to_equity_medium: float = 1.0
    current_ratio_high: float = 1.0
    current_ratio_medium: float = 1.2
    interest_coverage_high: float = 1.5
    interest_coverage_medium: float = 3.0
    margin_drop: float = 0.03
    terminal_value_share: float = 0.75
    sensitivity_range: float = 0.50
    premium_upside: float = -30.0
    min_evaluated: int = 3


@dataclass(frozen=True)
class RatingWeights:
    financial_health: float = 0.30
    valuation: float = 0.35
    risk: float = 0.25
    news: float = 0.10
    strong_buy: float = 4.25
    buy: float = 3.50
    hold: float = 2.75
    sell: float = 2.00


HEALTH = HealthThresholds()
VALUATION = ValuationThresholds()
RISK = RiskThresholds()
RATING = RatingWeights()

HEALTH_SCORES = {"STRONG": 5.0, "SOLID": 4.0, "MIXED": 3.0, "WEAK": 2.0}
VALUATION_SCORES = {
    "SIGNIFICANTLY_UNDERVALUED": 5.0,
    "SLIGHTLY_UNDERVALUED": 4.0,
    "FAIRLY_VALUED": 3.0,
    "SLIGHTLY_OVERVALUED": 2.0,
    "SIGNIFICANTLY_OVERVALUED": 1.0,
}
RISK_SCORES = {"LOW": 5.0, "MODERATE": 4.0, "ELEVATED": 2.0, "HIGH": 1.0}
SENTIMENT_SCORES = {
    "STRONGLY_BULLISH": 5.0,
    "BULLISH": 4.0,
    "NEUTRAL": 3.0,
    "BEARISH": 2.0,
    "STRONGLY_BEARISH": 1.0,
}

CYCLICAL_INDUSTRY_KEYWORDS = (
    "semiconductor",
    "auto",
    "airline",
    "oil",
    "gas",
    "energy",
    "steel",
    "mining",
    "hotel",
    "leisure",
    "homebuilding",
    "chemical",
)
FINANCIAL_INDUSTRY_KEYWORDS = ("bank", "insurance", "capital markets", "financial services", "asset management")
