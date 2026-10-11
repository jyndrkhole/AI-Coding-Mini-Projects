import boto3
import pytest

from app.ai.providers import complete


def test_resources_are_listed_and_filterable(client) -> None:
    body = client.get("/api/resources").json()
    assert len(body["resources"]) == 17
    dev = client.get("/api/resources", params={"environment": "dev"}).json()
    assert {row["resource_id"] for row in dev["resources"]} >= {"i-0devsched001", "vol-0devroot001"}
    detail = client.get("/api/resources/i-0prodapp001").json()
    assert "mysql" in detail["metadata"]["roles"]
    assert detail["metrics"][0]["metric_name"] == "CPUUtilization"


def test_recommendation_detail_and_status(client) -> None:
    rows = client.get("/api/recommendations").json()["recommendations"]
    first = rows[0]
    detail = client.get(f"/api/recommendations/{first['id']}").json()
    assert detail["title"] == first["title"]
    updated = client.patch(f"/api/recommendations/{first['id']}", json={"status": "REVIEWED"}).json()
    assert updated["status"] == "REVIEWED"
    rejected = client.patch(f"/api/recommendations/{first['id']}", json={"status": "DELETE"})
    assert rejected.status_code == 400


def test_business_hours_simulation_uses_stored_cost(client) -> None:
    body = client.post("/api/simulation", json={"scenario_type": "business_hours", "hours_per_weekday": 12, "environment": "dev"}).json()
    assert body["label"] == "ESTIMATE"
    assert body["included_resources"] == ["i-0devsched001"]
    assert body["current_monthly_cost"] == 2400
    assert body["potential_monthly_savings"] > 0
    assert body["projected_monthly_cost"] < body["current_monthly_cost"]
    assert any(line.startswith("ESTIMATE") for line in body["assumptions"])
    unsupported = client.post("/api/simulation", json={"scenario_type": "reserved_instances"})
    assert unsupported.status_code == 400


def test_monthly_report_uses_stored_totals(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.reports.complete", lambda system, user: None)
    missing = client.get("/api/reports/monthly")
    assert missing.status_code == 404
    created = client.post("/api/reports/monthly").json()
    assert "18420" in created["html"]
    assert created["total_cost"] == 18420
    assert "PDF export is not generated yet." in created["html"]
    assert client.get("/api/reports/monthly").json()["id"] == created["id"]


def test_advisor_explains_stored_evidence_without_calling_aws(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_aws_call(*args, **kwargs):
        raise AssertionError("AWS was called")

    monkeypatch.setattr(boto3, "client", reject_aws_call)
    monkeypatch.setattr(boto3, "Session", reject_aws_call)
    monkeypatch.setattr("app.ai.agent.complete", lambda system, user: "The stored evidence shows a development schedule opportunity.")
    answer = client.post("/api/ai/chat", json={"message": "Where can we reduce cost?"}).json()
    assert answer["narrative_source"] == "model"
    assert "18420" in " ".join(answer["facts"])
    monkeypatch.setattr("app.ai.agent.complete", lambda system, user: None)
    fallback = client.post("/api/ai/executive-summary").json()
    assert fallback["narrative_source"] == "evidence"
    assert "stored evidence" in fallback["narrative"].lower()


def test_provider_does_not_call_out_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert complete("system", "user") is None
    get_settings.cache_clear()


def test_xai_key_uses_the_xai_chat_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "xai")
    monkeypatch.setenv("GROQ_API_KEY", "xai-test")
    monkeypatch.setenv("GROQ_MODEL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    seen: dict = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["model"] = json["model"]
        assert headers["Authorization"] == "Bearer xai-test"
        return Response()

    monkeypatch.setattr("app.ai.providers.httpx.post", fake_post)
    assert complete("system", "user") == "ok"
    assert seen == {"url": "https://api.x.ai/v1/chat/completions", "model": "grok-4.7"}
    get_settings.cache_clear()
