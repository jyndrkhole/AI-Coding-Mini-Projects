"""FinOps advisor. Tools read stored evidence. The model may explain it and must not be the source of the numbers."""

from sqlalchemy.orm import Session

from app.ai.providers import complete
from app.core.config import get_settings
from app.core.exceptions import FinOpsError
from app.db.models import Resource
from app.services.account_service import require_account
from app.services.cost_service import get_cost_summary
from app.services.recommendation_service import get_recommendation, get_savings, list_recommendations

SYSTEM_PROMPT = """You are AWS Cost Guardian, an AI FinOps and cloud architecture advisor.

Explain only the evidence in the user message. Never invent AWS resources, costs, utilization, or savings.
Never claim guaranteed savings. If a figure is missing, say what evidence is required.
Never recommend a production change without validation. Never ask for AWS credentials.
Distinguish facts from assumptions. Estimated potential savings are not guaranteed."""


def chat(session: Session, message: str) -> dict:
    if not message.strip():
        raise FinOpsError("Enter a question for the advisor.", status_code=400)
    facts, missing = _account_facts(session, message)
    return _respond(message.strip(), facts, missing)


def explain(session: Session, recommendation_id: int) -> dict:
    item = get_recommendation(session, recommendation_id)
    facts = [
        f"Title: {item['title']}",
        f"Resource: {item['resource_id']}",
        f"Current monthly cost: {item['current_monthly_cost']}",
        f"Estimated potential monthly savings: {item['estimated_monthly_savings']}",
        f"Risk: {item['risk_level']}. Confidence: {item['confidence']}.",
        f"Evidence: {item['evidence_summary']}",
    ]
    facts.extend(f"Assumption: {assumption}" for assumption in item["assumptions"])
    missing = []
    if item["estimated_monthly_savings"] == 0:
        missing.append("No saving is stored for this recommendation.")
    return _respond(f"Explain recommendation {recommendation_id}.", facts, missing)


def executive_summary(session: Session) -> dict:
    facts, missing = _account_facts(session, "executive summary")
    return _respond("Write an executive summary from this evidence.", facts, missing)


def _respond(message: str, facts: list[str], missing: list[str]) -> dict:
    evidence = "\n".join(f"- {fact}" for fact in facts)
    gaps = "\n".join(f"- {item}" for item in missing) or "- None recorded."
    narrative = complete(SYSTEM_PROMPT, f"{message}\n\nFacts:\n{evidence}\n\nMissing evidence:\n{gaps}")
    settings = get_settings()
    provider = (settings.ai_provider or "none").lower()
    if provider == "groq" and settings.groq_api_key.startswith("xai-"):
        provider = "xai"
    if narrative:
        return {
            "provider": provider,
            "narrative_source": "model",
            "narrative": narrative,
            "facts": facts,
            "missing_evidence": missing,
        }
    return {
        "provider": provider,
        "narrative_source": "evidence",
        "narrative": _evidence_narrative(facts, missing),
        "facts": facts,
        "missing_evidence": missing,
    }


def _evidence_narrative(facts: list[str], missing: list[str]) -> str:
    lines = ["The advisor model did not answer. These points come from stored evidence:"]
    lines.extend(facts)
    if missing:
        lines.append("Still missing:")
        lines.extend(missing)
    return " ".join(lines)


def _account_facts(session: Session, message: str) -> tuple[list[str], list[str]]:
    account = require_account(session)
    summary = get_cost_summary(session)
    savings = get_savings(session)
    recommendations = list_recommendations(session)["recommendations"]
    facts = [
        f"Account {account.aws_account_id} in {account.region}.",
        f"{summary['current_period_label']} cost {summary['current_monthly_cost']} {summary['currency']}.",
        f"{summary['previous_period_label']} cost {summary['previous_monthly_cost']} {summary['currency']}.",
        f"{savings['label']} {savings['potential_monthly_savings']} {savings['currency']} per month.",
    ]
    for item in recommendations[:5]:
        facts.append(
            f"{item['title']}: current {item['current_monthly_cost']}, estimated potential savings {item['estimated_monthly_savings']} {summary['currency']}, risk {item['risk_level']}."
        )
    missing = []
    if not recommendations:
        missing.append("No recommendations are stored for this account.")
    lowered = message.lower()
    if "nat" in lowered:
        nats = (
            session.query(Resource)
            .filter(Resource.account_id == account.id, Resource.resource_type == "nat_gateway")
            .all()
        )
        if nats:
            facts.append("NAT gateways stored: " + ", ".join(row.resource_id for row in nats))
        else:
            missing.append("No NAT gateway is stored in inventory.")
    return facts, missing
