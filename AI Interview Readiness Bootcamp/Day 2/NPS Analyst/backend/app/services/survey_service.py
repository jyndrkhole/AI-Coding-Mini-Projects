"""Ingest a survey CSV into the analysis tables."""

from __future__ import annotations

import hashlib
import json
import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import survey_path
from app.core.exceptions import DatasetNotFound, NotFoundError
from app.data.loader import load_survey_csv
from app.data.normalizer import normalize
from app.data.validator import validate_frame
from app.db import repositories
from app.db.models import DataQualityIssue, SurveyDataset, SurveyResponse


def _jsonable(value):
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def ingest_frame(session: Session, frame: pd.DataFrame, filename: str, checksum: str) -> str:
    existing = repositories.dataset_by_checksum(session, checksum)
    if existing is not None:
        return existing.id
    validation = validate_frame(frame)
    responses = normalize(frame, validation)
    dataset_id = str(uuid.uuid4())
    dates = [row.date for row in responses]
    dataset = SurveyDataset(
        id=dataset_id,
        filename=filename,
        checksum=checksum,
        row_count=validation.original_rows,
        valid_count=len(responses),
        reporting_period_start=min(dates) if dates else None,
        reporting_period_end=max(dates) if dates else None,
        uploaded_at=repositories.now(),
    )
    stored = []
    for position, normalized in zip(validation.valid_index, responses):
        source = frame.loc[position]
        raw = {column: _jsonable(source[column]) for column in frame.columns}
        stored.append(
            SurveyResponse(
                dataset_id=dataset_id,
                response_id=normalized.response_id,
                date=normalized.date,
                month=normalized.month,
                product=normalized.product,
                tenure=normalized.tenure,
                channel=normalized.channel,
                score=normalized.score,
                comment=normalized.comment,
                annual_revenue_inr=normalized.annual_revenue_inr,
                raw_record_json=json.dumps(raw),
            )
        )
    issues = [
        DataQualityIssue(
            dataset_id=dataset_id,
            response_id=issue.response_id,
            issue_type=issue.issue_type,
            severity=issue.severity,
            evidence_json=json.dumps(issue.evidence, default=str),
        )
        for issue in validation.issues
    ]
    repositories.save_dataset(session, dataset, stored, issues)
    return dataset_id


def ingest_path(session: Session, path) -> str:
    frame = load_survey_csv(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return ingest_frame(session, frame, path.name, digest)


def ensure_default(session: Session) -> str | None:
    path = survey_path()
    if not path.exists():
        return None
    return ingest_path(session, path)


def require_dataset(session: Session, dataset_id: str) -> SurveyDataset:
    dataset = repositories.dataset_by_id(session, dataset_id)
    if dataset is None:
        raise NotFoundError(f"Dataset {dataset_id} was not found.")
    return dataset
