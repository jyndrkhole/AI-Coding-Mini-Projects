from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.themes import examples_for
from app.api.deps import db_session, require_access
from app.core.exceptions import NotFoundError
from app.services.analysis_service import bundle_for

router = APIRouter(prefix="/api", tags=["themes"], dependencies=[Depends(require_access)])


def _bundle(session: Session, dataset_id: str) -> dict:
    try:
        return bundle_for(session, dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _public_theme(bundle: dict, theme: dict) -> dict:
    public = {key: value for key, value in theme.items()}
    public["negative_examples"] = examples_for(bundle["classified"], theme["theme"], "NEGATIVE", 2)
    public["positive_examples"] = examples_for(bundle["classified"], theme["theme"], "POSITIVE", 1)
    return public


@router.get("/themes/{dataset_id}")
def themes(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    return {
        "themes": [_public_theme(bundle, theme) for theme in bundle["themes"]],
        "association": bundle["association"],
        "priorities": bundle["priorities"],
    }


@router.get("/themes/{dataset_id}/monthly")
def themes_monthly(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    bundle = _bundle(session, dataset_id)
    return {"themes": [{"theme": theme["theme"], "monthly": theme["monthly"], "detractor_change": theme["detractor_change"]} for theme in bundle["themes"]]}
