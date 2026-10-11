from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.recommendation import RecommendationListResponse, RecommendationResponse, RecommendationStatusUpdate
from app.services.recommendation_service import get_recommendation, list_recommendations, update_recommendation_status

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationListResponse)
def recommendations(session: Session = Depends(get_db)) -> RecommendationListResponse:
    return RecommendationListResponse(**list_recommendations(session))


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def recommendation_detail(recommendation_id: int, session: Session = Depends(get_db)) -> RecommendationResponse:
    return RecommendationResponse(**get_recommendation(session, recommendation_id))


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def recommendation_status(
    recommendation_id: int,
    body: RecommendationStatusUpdate,
    session: Session = Depends(get_db),
) -> RecommendationResponse:
    return RecommendationResponse(**update_recommendation_status(session, recommendation_id, body.status))
