from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.agent import chat, executive_summary, explain
from app.db.database import get_db
from app.schemas.recommendation import AdvisorChatRequest, AdvisorExplainRequest, AdvisorResponse

router = APIRouter(tags=["advisor"])


@router.post("/ai/chat", response_model=AdvisorResponse)
def ai_chat(body: AdvisorChatRequest, session: Session = Depends(get_db)) -> AdvisorResponse:
    return AdvisorResponse(**chat(session, body.message))


@router.post("/ai/explain", response_model=AdvisorResponse)
def ai_explain(body: AdvisorExplainRequest, session: Session = Depends(get_db)) -> AdvisorResponse:
    return AdvisorResponse(**explain(session, body.recommendation_id))


@router.post("/ai/executive-summary", response_model=AdvisorResponse)
def ai_executive_summary(session: Session = Depends(get_db)) -> AdvisorResponse:
    return AdvisorResponse(**executive_summary(session))
