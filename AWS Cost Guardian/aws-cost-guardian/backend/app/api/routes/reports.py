from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.providers import complete
from app.ai.agent import SYSTEM_PROMPT, _account_facts
from app.db.database import get_db
from app.schemas.recommendation import ReportResponse
from app.services.report_service import generate_monthly_report, latest_monthly_report

router = APIRouter(tags=["reports"])


@router.get("/reports/monthly", response_model=ReportResponse)
def monthly_report(session: Session = Depends(get_db)) -> ReportResponse:
    return ReportResponse(**latest_monthly_report(session))


@router.post("/reports/monthly", response_model=ReportResponse)
def create_monthly_report(session: Session = Depends(get_db)) -> ReportResponse:
    facts, missing = _account_facts(session, "monthly report")
    narrative = complete(SYSTEM_PROMPT, "Write an executive summary.\n" + "\n".join(facts + missing))
    return ReportResponse(**generate_monthly_report(session, narrative))
