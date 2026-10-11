from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.recommendation import SimulationRequest, SimulationResponse
from app.services.simulation_service import run_simulation

router = APIRouter(tags=["simulation"])


@router.post("/simulation", response_model=SimulationResponse)
def simulation(body: SimulationRequest, session: Session = Depends(get_db)) -> SimulationResponse:
    return SimulationResponse(**run_simulation(session, body.scenario_type, body.hours_per_weekday, body.environment))
