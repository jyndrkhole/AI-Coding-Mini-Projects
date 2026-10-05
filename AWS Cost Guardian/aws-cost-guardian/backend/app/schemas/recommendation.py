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
