from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.recommendation import RecommendationListResponse
from app.services.recommendation_service import list_recommendations

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationListResponse)
def recommendations(session: Session = Depends(get_db)) -> RecommendationListResponse:
    return RecommendationListResponse(**list_recommendations(session))
