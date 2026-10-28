import hashlib
import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_access
from app.core.config import MAX_UPLOAD_BYTES
from app.core.exceptions import DatasetSchemaError, NotFoundError
from app.db import repositories
from app.services import survey_service

router = APIRouter(prefix="/api/surveys", tags=["surveys"], dependencies=[Depends(require_access)])


def _dataset_dict(row, session: Session) -> dict:
    latest = repositories.latest_run(session, row.id)
    return {
        "id": row.id,
        "filename": row.filename,
        "checksum": row.checksum,
        "row_count": row.row_count,
        "valid_count": row.valid_count,
        "invalid_count": row.row_count - row.valid_count,
        "reporting_period_start": row.reporting_period_start,
        "reporting_period_end": row.reporting_period_end,
        "uploaded_at": row.uploaded_at.isoformat(),
        "latest_analysis_run_id": latest.id if latest else None,
    }


@router.get("/datasets")
def list_datasets(session: Session = Depends(db_session)) -> dict:
    return {"datasets": [_dataset_dict(row, session) for row in repositories.list_datasets(session)]}


@router.post("/upload")
async def upload(file: UploadFile = File(...), session: Session = Depends(db_session)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    payload = await file.read()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than the 2 MB upload limit.")
    try:
        frame = pd.read_csv(io.BytesIO(payload))
    except pd.errors.ParserError as exc:
        raise HTTPException(status_code=400, detail="The CSV could not be parsed.") from exc
    try:
        dataset_id = survey_service.ingest_frame(session, frame, file.filename, hashlib.sha256(payload).hexdigest())
    except (DatasetSchemaError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dataset = repositories.dataset_by_id(session, dataset_id)
    return _dataset_dict(dataset, session)


@router.get("/{dataset_id}/metadata")
def metadata(dataset_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        dataset = survey_service.require_dataset(session, dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _dataset_dict(dataset, session)
