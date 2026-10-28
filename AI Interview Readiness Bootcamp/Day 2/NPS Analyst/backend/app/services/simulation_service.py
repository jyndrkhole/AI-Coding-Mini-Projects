"""Hypothetical fix simulations. They do not rewrite the stored survey."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.analytics.simulation import simulate_fix
from app.db import repositories
from app.db.models import SimulationRun
from app.services.analysis_service import bundle_for


def run_simulation(session: Session, dataset_id: str, theme: str, scenario: str, proportion: float, score_delta: int, response_ids: list[str] | None) -> dict:
    bundle = bundle_for(session, dataset_id)
    theme_by_id = {item["response_id"]: item["primary_theme"] for item in bundle["classified"]}
    result = simulate_fix(
        bundle["responses"],
        theme_by_id,
        theme,
        scenario,
        proportion=proportion,
        score_delta=score_delta,
        response_ids=response_ids,
    )
    latest = repositories.latest_run(session, dataset_id)
    repositories.save_simulation(
        session,
        SimulationRun(
            id=str(uuid.uuid4()),
            analysis_run_id=latest.id if latest else None,
            scenario_type=scenario,
            parameters_json=json.dumps(
                {"dataset_id": dataset_id, "theme": theme, "scenario": scenario, "proportion": proportion, "score_delta": score_delta, "response_ids": response_ids}
            ),
            result_json=json.dumps(result),
            created_at=repositories.now(),
        ),
    )
    return result
