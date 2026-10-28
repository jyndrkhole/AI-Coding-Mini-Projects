from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_access
from app.core.exceptions import NotFoundError
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_access)])


@router.get("/{analysis_run_id}")
def report(analysis_run_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        return report_service.load_report(session, analysis_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{analysis_run_id}/export")
def export(analysis_run_id: str, format: str = "md", session: Session = Depends(db_session)):
    try:
        document = report_service.load_report(session, analysis_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if format == "html":
        return HTMLResponse(report_service.to_html(document))
    if format == "md":
        return PlainTextResponse(report_service.to_markdown(document), media_type="text/markdown")
    raise HTTPException(status_code=400, detail="format must be md or html.")
