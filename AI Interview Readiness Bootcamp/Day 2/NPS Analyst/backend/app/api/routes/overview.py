from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_access
from app.core.exceptions import NotFoundError
from app.services.analysis_service import bundle_for

router = APIRouter(prefix="/api", tags=["overview"], dependencies=[Depends(require_access)])


def _bundle(session: Session, dataset_id: str) -> dict:
    try:
        return bundle_for(session, dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/overview/{dataset_id}")
def overview(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    overview_row = bundle["overview"]
    return {
        "dataset_id": dataset_id,
        "metadata": bundle["metadata"],
        **overview_row,
        "alert": bundle["alert"],
        "period": bundle["period"],
        "revenue_exposed_inr": bundle["revenue"]["revenue_exposed_inr"],
        "estimated_expected_revenue_at_risk_inr": bundle["revenue"]["estimated_expected_revenue_at_risk_inr"],
        "assumptions": bundle["revenue"]["assumptions"],
        "missing_revenue_count": bundle["revenue"]["missing_revenue_count"],
        "coverage_percentage": bundle["revenue"]["coverage_percentage"],
        "monthly": bundle["months"],
        "by_product": bundle["segments"]["product"],
        "by_channel": bundle["segments"]["channel"],
        "by_tenure": bundle["segments"]["tenure"],
        "top_themes": bundle["themes"][:8],
        "reference_claims": bundle["reference_claims"],
        "association": bundle["association"],
    }


@router.get("/nps/{dataset_id}/monthly")
def monthly(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    return {"months": bundle["months"], "period": bundle["period"], "reference_claims": bundle["reference_claims"]}


@router.get("/nps/{dataset_id}/segments")
def segments(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    return {"segments": bundle["segments"]}


@router.get("/nps/{dataset_id}/confidence")
def confidence(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    confidence_block = bundle["confidence"]
    return {
        "overall": confidence_block["overall"],
        "months": confidence_block["months"],
        "segments": confidence_block["segments"],
        "minimum_sample": confidence_block["minimum_sample"],
        "ranking_note": confidence_block["ranking_note"],
    }
