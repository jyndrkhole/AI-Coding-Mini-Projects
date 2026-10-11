from pydantic import BaseModel


class MonthComponentChange(BaseModel):
    service: str
    usage_type: str
    change: float


class MonthCostPoint(BaseModel):
    month: str
    label: str
    amount: float
    partial: bool
    compared_to: str | None = None
    change: float | None = None
    change_percent: float | None = None
    components: list[MonthComponentChange] = []
    other_component_count: int = 0


class CostSummaryResponse(BaseModel):
    currency: str
    current_period_label: str
    previous_period_label: str
    current_monthly_cost: float
    previous_monthly_cost: float
    mom_change_amount: float
    mom_change_percent: float | None
    mock_aws: bool
    history_note: str
    prior_months_average: float | None
    months: list[MonthCostPoint]


class DailyCostPoint(BaseModel):
    date: str
    amount: float


class DailyCostResponse(BaseModel):
    currency: str
    period_label: str
    points: list[DailyCostPoint]


class ServiceCost(BaseModel):
    service: str
    current: float
    previous: float
    change: float
    change_percent: float | None


class ServiceCostResponse(BaseModel):
    currency: str
    current_period_label: str
    previous_period_label: str
    services: list[ServiceCost]


class RegionCost(BaseModel):
    region: str
    current: float
    previous: float
    change: float
    change_percent: float | None


class RegionCostResponse(BaseModel):
    currency: str
    current_period_label: str
    previous_period_label: str
    regions: list[RegionCost]


class MonthlyCostPoint(BaseModel):
    month: str
    label: str
    amount: float


class UsageCost(BaseModel):
    service: str
    usage_type: str
    current: float
    previous: float
    change: float
    change_percent: float | None
    pricing_available: bool


class CostExplorerResponse(BaseModel):
    currency: str
    source_label: str
    start: str
    end: str
    service: str | None
    region: str | None
    current_period_label: str
    previous_period_label: str
    available_services: list[str]
    available_regions: list[str]
    daily_note: str | None
    monthly_note: str
    pricing_note: str | None
    daily: list[DailyCostPoint]
    monthly: list[MonthlyCostPoint]
    services: list[ServiceCost]
    regions: list[RegionCost]
    usage_types: list[UsageCost]


class PriceQuoteResponse(BaseModel):
    pricing_available: bool
    amount: float | None
    currency: str | None
    unit: str | None
    reason: str
