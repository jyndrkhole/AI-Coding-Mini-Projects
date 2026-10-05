from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.cost import (
    CostExplorerResponse,
    CostSummaryResponse,
    DailyCostResponse,
    PriceQuoteResponse,
    RegionCostResponse,
    ServiceCostResponse,
)
from app.services.cost_service import (
    get_cost_explorer,
    get_cost_summary,
    get_daily_costs,
    get_region_costs,
    get_service_costs,
)
from app.services.pricing_service import PricingService

router = APIRouter(tags=["costs"])


@router.get("/costs/summary", response_model=CostSummaryResponse)
def cost_summary(session: Session = Depends(get_db)) -> CostSummaryResponse:
    return CostSummaryResponse(**get_cost_summary(session))


@router.get("/costs/daily", response_model=DailyCostResponse)
def daily_costs(session: Session = Depends(get_db)) -> DailyCostResponse:
    return DailyCostResponse(**get_daily_costs(session))


@router.get("/costs/services", response_model=ServiceCostResponse)
def service_costs(session: Session = Depends(get_db)) -> ServiceCostResponse:
    return ServiceCostResponse(**get_service_costs(session))


@router.get("/costs/regions", response_model=RegionCostResponse)
def region_costs(session: Session = Depends(get_db)) -> RegionCostResponse:
    return RegionCostResponse(**get_region_costs(session))


@router.get("/costs/explorer", response_model=CostExplorerResponse)
def cost_explorer(
    start: date | None = None,
    end: date | None = None,
    service: str | None = None,
    region: str | None = None,
    session: Session = Depends(get_db),
) -> CostExplorerResponse:
    return CostExplorerResponse(**get_cost_explorer(session, start, end, service or None, region or None))


@router.get("/costs/pricing", response_model=PriceQuoteResponse)
def cost_pricing(service: str, usage_type: str, region: str = "all") -> PriceQuoteResponse:
    return PriceQuoteResponse(**PricingService().quote(service, usage_type, region))
