"""Pydantic contracts shared by agents, the API, and the report."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HealthLabel = Literal["STRONG", "SOLID", "MIXED", "WEAK", "INSUFFICIENT_DATA"]
ValuationLabel = Literal[
    "SIGNIFICANTLY_UNDERVALUED",
    "SLIGHTLY_UNDERVALUED",
    "FAIRLY_VALUED",
    "SLIGHTLY_OVERVALUED",
    "SIGNIFICANTLY_OVERVALUED",
    "INSUFFICIENT_DATA",
]
RiskLabel = Literal["LOW", "MODERATE", "ELEVATED", "HIGH", "INSUFFICIENT_DATA"]
SentimentLabel = Literal[
    "STRONGLY_BULLISH",
    "BULLISH",
    "NEUTRAL",
    "BEARISH",
    "STRONGLY_BEARISH",
    "INSUFFICIENT_DATA",
]
RatingLabel = Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "INSUFFICIENT_DATA"]
Confidence = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
Unit = Literal["percent", "ratio", "currency", "per_share", "multiple", "number"]


class Metric(BaseModel):
    key: str
    label: str
    value: float | None
    unit: Unit
    formula: str
    period: str | None = None
    note: str | None = None
    interpretable: bool = True


class Assumption(BaseModel):
    key: str
    label: str
    value: float | list[float] | str | None
    source: Literal["historical", "analyst_input", "model_estimate", "market"]
    rationale: str


class PeriodFinancials(BaseModel):
    period_end: str
    period_type: Literal["annual", "quarter"]
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    interest_expense: float | None = None
    tax_provision: float | None = None
    pretax_income: float | None = None
    eps: float | None = None
    depreciation: float | None = None
    cash: float | None = None
    cash_definition: str | None = None
    total_assets: float | None = None
    current_assets: float | None = None
    inventory: float | None = None
    total_liabilities: float | None = None
    current_liabilities: float | None = None
    total_debt: float | None = None
    equity: float | None = None
    shares: float | None = None
    minority_interest: float | None = None
    preferred_stock: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    dividends: float | None = None
    change_in_working_capital: float | None = None


class MarketSnapshot(BaseModel):
    ticker: str
    company_name: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    price: float | None = None
    previous_close: float | None = None
    price_as_of: str | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    enterprise_value_source: str | None = None
    shares: float | None = None
    shares_source: str | None = None
    beta: float | None = None
    trailing_pe: float | None = None
    dividend_yield: float | None = None


class CompanySnapshot(BaseModel):
    market: MarketSnapshot
    annual: list[PeriodFinancials] = Field(default_factory=list)
    quarterly: list[PeriodFinancials] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class NewsArticle(BaseModel):
    id: str
    title: str
    publisher: str | None = None
    published_at: str | None = None
    url: str | None = None
    summary: str | None = None
    category: str = "other"
    sentiment: SentimentLabel = "NEUTRAL"
    sentiment_reason: str = ""
    mentions_company: bool = True


class HistoryPoint(BaseModel):
    period: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    equity: float | None = None
    total_debt: float | None = None
    cash: float | None = None


class HealthResult(BaseModel):
    label: HealthLabel
    score: float | None
    basis: Literal["general_heuristic", "financial_company_heuristic"]
    checks_passed: int
    checks_evaluated: int
    metrics: list[Metric] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    history: list[HistoryPoint] = Field(default_factory=list)


class ForecastYear(BaseModel):
    year: int
    revenue: float | None = None
    free_cash_flow: float
    discount_factor: float
    present_value: float


class SensitivityCell(BaseModel):
    discount_rate: float
    terminal_growth: float
    value_per_share: float


class ScenarioResult(BaseModel):
    name: Literal["bull", "base", "bear"]
    intrinsic_value_per_share: float | None
    upside_percent: float | None
    assumptions: list[Assumption]
    note: str


class PeerMultiple(BaseModel):
    ticker: str
    name: str | None = None
    price_to_earnings: float | None = None
    price_to_sales: float | None = None
    price_to_book: float | None = None
    ev_to_ebitda: float | None = None
    ev_to_revenue: float | None = None
    excluded_reason: str | None = None


class DCFResult(BaseModel):
    status: Literal["ok", "unreliable", "unavailable"]
    model: Literal["fcff_wacc", "fcfe_cost_of_equity", "none"]
    methodology: str
    intrinsic_value_per_share: float | None = None
    enterprise_value: float | None = None
    equity_value: float | None = None
    discount_rate: float | None = None
    terminal_growth: float | None = None
    terminal_value: float | None = None
    terminal_value_share: float | None = None
    forecast: list[ForecastYear] = Field(default_factory=list)
    sensitivity: list[SensitivityCell] = Field(default_factory=list)
    margin_sensitivity: list[dict[str, float | None]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ValuationResult(BaseModel):
    label: ValuationLabel
    method_used: str
    intrinsic_value_per_share: float | None = None
    current_price: float | None = None
    difference: float | None = None
    upside_percent: float | None = None
    dcf: DCFResult
    peers: list[PeerMultiple] = Field(default_factory=list)
    peer_median: dict[str, float | None] = Field(default_factory=dict)
    peer_mean: dict[str, float | None] = Field(default_factory=dict)
    peer_implied_value: float | None = None
    peer_selection: str = ""
    excluded_peers: list[str] = Field(default_factory=list)
    target_multiples: PeerMultiple | None = None
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RiskFlag(BaseModel):
    category: Literal["financial", "valuation", "business", "news"]
    severity: Literal["low", "medium", "high"]
    title: str
    evidence: str
    impact: str


class RiskResult(BaseModel):
    label: RiskLabel
    flags: list[RiskFlag]
    evaluated_signals: int
    methodology: str
    limitations: list[str]


class NewsResult(BaseModel):
    label: SentimentLabel
    lookback_days: int
    articles: list[NewsArticle] = Field(default_factory=list)
    catalysts_positive: list[str] = Field(default_factory=list)
    catalysts_negative: list[str] = Field(default_factory=list)
    method: Literal["llm", "lexicon", "unavailable"]
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence


class ComponentScore(BaseModel):
    name: str
    label: str
    score: float | None
    weight: float
    critical: bool


class Assessment(BaseModel):
    label: RatingLabel
    score: float | None
    confidence: Confidence
    components: list[ComponentScore]
    weight_notes: list[str]
    methodology: str


class Disagreement(BaseModel):
    financial_health: HealthLabel
    valuation: ValuationLabel
    risk: RiskLabel
    news: SentimentLabel
    conflicts: list[str]
    consistent: bool


class DataQuality(BaseModel):
    confidence: Confidence
    years_annual: int
    missing_fields: list[str]
    limitations: list[str]
    coverage_score: float


class ReportSection(BaseModel):
    id: str
    title: str
    paragraphs: list[str]
    bullets: list[str] = Field(default_factory=list)
    interpretation: str | None = None
    interpretation_source: Literal["llm", "rules", "none"] = "none"


class TraceSpan(BaseModel):
    name: str
    phase: str
    started_offset_ms: float
    duration_ms: float


class LLMInfo(BaseModel):
    provider: str
    model: str
    used: bool
    message: str


class AnalysisReport(BaseModel):
    id: str
    ticker: str
    company_name: str
    created_at: str
    currency: str | None
    rating: Assessment
    disagreement: Disagreement
    market: MarketSnapshot
    health: HealthResult
    valuation: ValuationResult
    risk: RiskResult
    news: NewsResult
    data_quality: DataQuality
    assumptions: list[Assumption]
    sections: list[ReportSection]
    brief_markdown: str
    trace: list[TraceSpan]
    llm: LLMInfo
    disclaimer: str


class AssumptionOverrides(BaseModel):
    forecast_years: int = 5
    revenue_growth: float | None = None
    operating_margin: float | None = None
    tax_rate: float | None = None
    capex_pct_revenue: float | None = None
    nwc_pct_revenue: float | None = None
    da_pct_revenue: float | None = None
    discount_rate: float | None = None
    terminal_growth: float | None = None
    risk_free_rate: float = 0.042
    equity_risk_premium: float = 0.05


class AnalyzeRequest(BaseModel):
    ticker: str
    news_lookback_days: int = 30
    peers: list[str] | None = None
    assumptions: AssumptionOverrides | None = None
