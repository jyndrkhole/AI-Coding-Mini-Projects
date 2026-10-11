from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    id: int
    resource_id: str | None
    title: str
    description: str
    service: str
    category: str
    current_monthly_cost: float
    estimated_monthly_savings: float
    estimated_annual_savings: float
    confidence: str
    data_quality: str
    risk_level: str
    priority: int
    action_type: str
    source: str
    status: str
    evidence_summary: str
    assumptions: list[str]
    client_brief: str = ""
    client_ask: str = ""
    next_steps: list[str] = []
    rule_id: str | None = None
    currency: str | None = None


class RecommendationListResponse(BaseModel):
    currency: str
    recommendations: list[RecommendationResponse]


class SavingsResponse(BaseModel):
    currency: str
    label: str
    potential_monthly_savings: float
    potential_annual_savings: float
    safe_monthly_savings: float
    review_monthly_savings: float
    architecture_monthly_savings: float


class OptimizationScoreResponse(BaseModel):
    score: int | None
    maximum: int
    source: str
    label: str
    strengths: list[str] = []
    opportunities: list[str] = []
    top_improvements: list[str] = []


class RecommendationStatusUpdate(BaseModel):
    status: str


class AdvisorResponse(BaseModel):
    provider: str
    narrative_source: str
    narrative: str
    facts: list[str]
    missing_evidence: list[str]


class AdvisorChatRequest(BaseModel):
    message: str


class AdvisorExplainRequest(BaseModel):
    recommendation_id: int


class SimulationRequest(BaseModel):
    scenario_type: str = "business_hours"
    hours_per_weekday: int = 12
    environment: str = "dev"


class SimulationResponse(BaseModel):
    id: int
    label: str
    scenario_type: str
    currency: str
    current_monthly_cost: float
    projected_monthly_cost: float
    potential_monthly_savings: float
    potential_annual_savings: float
    included_resources: list[str]
    excluded_resources: list[str]
    assumptions: list[str]
    risk_level: str


class ReportResponse(BaseModel):
    id: int
    report_month: str
    currency: str
    total_cost: float
    previous_month_cost: float
    potential_savings: float
    realized_savings: float
    html: str
    narrative: str | None = None
