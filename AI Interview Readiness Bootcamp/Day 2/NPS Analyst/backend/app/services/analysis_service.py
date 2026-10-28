"""Run and cache the deterministic bundle, then the agent orchestration."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_orchestrator
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db import repositories
from app.db.models import AnalysisRun
from app.services.bundle import build_bundle
from app.services.survey_service import require_dataset

_CACHE: dict[tuple, dict] = {}


def bundle_for(session: Session, dataset_id: str) -> dict:
    dataset = require_dataset(session, dataset_id)
    settings = get_settings()
    key = (dataset.id, dataset.checksum, settings.fingerprint())
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    responses = repositories.responses_for(session, dataset.id)
    issues = repositories.validation_issues(session, dataset.id)
    metadata = {
        "dataset_id": dataset.id,
        "filename": dataset.filename,
        "checksum": dataset.checksum,
        "row_count": dataset.row_count,
        "valid_count": dataset.valid_count,
        "invalid_count": dataset.row_count - dataset.valid_count,
        "reporting_period_start": dataset.reporting_period_start,
        "reporting_period_end": dataset.reporting_period_end,
        "uploaded_at": dataset.uploaded_at.isoformat(),
    }
    bundle = build_bundle(responses, issues, settings, metadata)
    _CACHE[key] = bundle
    return bundle


def clear_cache() -> None:
    _CACHE.clear()


async def run_analysis(session: Session, dataset_id: str, force: bool = False) -> dict:
    dataset = require_dataset(session, dataset_id)
    settings = get_settings()
    fingerprint = settings.fingerprint()
    existing = repositories.latest_run(session, dataset.id)
    if existing is not None and not force and existing.config_fingerprint == fingerprint and existing.result_json:
        return {"analysis_run_id": existing.id, "status": existing.status, "reused": True, "result": json.loads(existing.result_json)}
    bundle = bundle_for(session, dataset.id)
    started = repositories.now()
    result = await run_orchestrator(bundle)
    public = {
        "status": result["status"],
        "trace": result["trace"],
        "specialists": result["specialists"],
        "report": result["report"],
        "fact_check": result["fact_check"],
        "themes": bundle["themes"],
        "overview": bundle["overview"],
        "alert": bundle["alert"],
    }
    run = AnalysisRun(
        id=str(uuid.uuid4()),
        dataset_id=dataset.id,
        status=result["status"],
        config_fingerprint=fingerprint,
        started_at=started,
        completed_at=repositories.now(),
        result_json=json.dumps(public),
        error_json=None,
    )
    repositories.save_run(session, run, public)
    repositories.replace_classifications(session, dataset.id, bundle["classified"])
    return {"analysis_run_id": run.id, "status": run.status, "reused": False, "result": public}


def stored_result(session: Session, run_id: str) -> dict:
    run = repositories.run_by_id(session, run_id)
    if run is None or not run.result_json:
        raise NotFoundError(f"Analysis run {run_id} was not found.")
    return {"analysis_run_id": run.id, "dataset_id": run.dataset_id, "status": run.status, "result": json.loads(run.result_json)}
