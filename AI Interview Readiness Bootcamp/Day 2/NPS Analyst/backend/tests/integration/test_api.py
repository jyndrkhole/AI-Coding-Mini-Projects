"""API checks that do not call a model provider."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.database import reset_engine
from app.main import create_app
from app.services.analysis_service import clear_cache


def client(tmp_path: Path) -> TestClient:
    os.environ["NPS_DATABASE_URL"] = f"sqlite:///{tmp_path / 'nps.db'}"
    os.environ["NPS_BOOTSTRAP_SAMPLES"] = "30"
    os.environ["NPS_SKIP_AUTO_ANALYSIS"] = "1"
    reset_engine()
    clear_cache()
    return TestClient(create_app())


def test_health_overview_analysis_and_unknown_dataset(tmp_path):
    with client(tmp_path) as api:
        health = api.get("/api/health")
        assert health.status_code == 200
        assert health.json()["deterministic_only"] is True
        datasets = api.get("/api/surveys/datasets")
        assert datasets.status_code == 200
        dataset_id = datasets.json()["datasets"][0]["id"]
        overview = api.get(f"/api/overview/{dataset_id}")
        assert overview.status_code == 200
        body = overview.json()
        assert body["total_responses"] == 600
        assert body["alert"]["level"] == "RED"
        missing = api.get("/api/overview/does-not-exist")
        assert missing.status_code == 404
        uploaded = api.post(
            "/api/surveys/upload",
            files={"file": ("broken.csv", b"not,a,survey\n1,2,3\n", "text/csv")},
        )
        assert uploaded.status_code == 400
        run = api.post(f"/api/analysis/{dataset_id}/run")
        assert run.status_code == 200
        payload = run.json()
        assert payload["fact_check"]["passed"] is True
        report = api.get(f"/api/reports/{payload['analysis_run_id']}")
        assert report.status_code == 200
        assert report.json()["report"]["alert_level"] == "RED"
        exported = api.get(f"/api/reports/{payload['analysis_run_id']}/export", params={"format": "html"})
        assert exported.status_code == 200
        assert "<script" not in exported.text.lower()
        trace = api.get(f"/api/agents/{payload['analysis_run_id']}/trace")
        assert trace.status_code == 200
        assert any(step["phase"] == "phase_1" for step in trace.json()["trace"])
