from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.recommendation import OptimizationScoreResponse, SavingsResponse
from app.services.recommendation_service import get_optimization_score, get_savings

router = APIRouter(tags=["savings"])


@router.get("/savings", response_model=SavingsResponse)
def savings(session: Session = Depends(get_db)) -> SavingsResponse:
    return SavingsResponse(**get_savings(session))


@router.get("/optimization-score", response_model=OptimizationScoreResponse)
def optimization_score(session: Session = Depends(get_db)) -> OptimizationScoreResponse:
    return OptimizationScoreResponse(**get_optimization_score(session))
