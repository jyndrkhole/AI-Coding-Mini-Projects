import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_access
from app.core.exceptions import NotFoundError
from app.db import repositories
from app.services import analysis_service, simulation_service

router = APIRouter(prefix="/api", tags=["analysis"], dependencies=[Depends(require_access)])


class SimulationRequest(BaseModel):
    dataset_id: str
    theme: str
    scenario: str = Field(pattern="^[ABC]$")
    proportion: float = 1
    score_delta: int = 2
    response_ids: list[str] | None = None


@router.get("/callbacks/{analysis_run_id}")
def callbacks(analysis_run_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        stored = analysis_service.stored_result(session, analysis_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"analysis_run_id": analysis_run_id, "candidates": stored["result"]["report"].get("callbacks", [])}


@router.post("/analysis/{dataset_id}/run")
async def run(dataset_id: str, force: bool = False, session: Session = Depends(db_session)) -> dict:
    try:
        result = await analysis_service.run_analysis(session, dataset_id, force=force)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"analysis_run_id": result["analysis_run_id"], "status": result["status"], "reused": result["reused"], "fact_check": result["result"]["fact_check"], "alert_level": result["result"]["report"]["alert_level"]}


@router.get("/analysis/{analysis_run_id}/status")
def status(analysis_run_id: str, session: Session = Depends(db_session)) -> dict:
    run_row = repositories.run_by_id(session, analysis_run_id)
    if run_row is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    return {"analysis_run_id": run_row.id, "dataset_id": run_row.dataset_id, "status": run_row.status, "started_at": run_row.started_at.isoformat(), "completed_at": run_row.completed_at.isoformat() if run_row.completed_at else None}


@router.get("/analysis/{analysis_run_id}/results")
def results(analysis_run_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        return analysis_service.stored_result(session, analysis_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/simulations/fix-impact")
def simulate(body: SimulationRequest, session: Session = Depends(db_session)) -> dict:
    try:
        if not 0 <= body.proportion <= 1:
            raise HTTPException(status_code=400, detail="proportion must be between 0 and 1.")
        return simulation_service.run_simulation(
            session,
            body.dataset_id,
            body.theme,
            body.scenario,
            body.proportion,
            body.score_delta,
            body.response_ids,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/agents/{analysis_run_id}/trace")
def trace(analysis_run_id: str, session: Session = Depends(db_session)) -> dict:
    try:
        stored = analysis_service.stored_result(session, analysis_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rows = repositories.trace_for_run(session, analysis_run_id)
    return {
        "analysis_run_id": analysis_run_id,
        "trace": stored["result"]["trace"],
        "stored_steps": [
            {"agent": row.agent_name, "phase": row.phase, "status": row.status, "duration_ms": row.duration_ms, "error": json.loads(row.error_json) if row.error_json else None}
            for row in rows
        ],
    }
