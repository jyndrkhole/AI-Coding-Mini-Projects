from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_access
from app.core.exceptions import NotFoundError
from app.services.analysis_service import bundle_for

router = APIRouter(prefix="/api", tags=["risk"], dependencies=[Depends(require_access)])


@router.get("/data-quality/{dataset_id}")
def data_quality(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        bundle = bundle_for(session, dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    quality = bundle["quality"]
    return {
        "total_issues": quality["total_issues"],
        "by_type": quality["by_type"],
        "contradiction_count": quality["contradiction_count"],
        "missing_comment_count": quality["missing_comment_count"],
        "missing_revenue_count": quality["missing_revenue_count"],
        "note": quality["note"],
        "issues": quality["issues"],
    }


@router.get("/revenue-risk/{dataset_id}")
def revenue_risk(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        bundle = bundle_for(session, dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    revenue = {key: value for key, value in bundle["revenue"].items() if key != "per_response"}
    revenue["high_value_detractors"] = [
        row for row in bundle["callbacks"] if row["nps_classification"] == "detractor"
    ][:15]
    revenue["priorities"] = bundle["priorities"]
    return revenue
