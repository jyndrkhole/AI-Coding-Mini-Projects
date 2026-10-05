"""Read stored recommendations and sum their estimated savings."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import FinOpsError
from app.core.money import as_decimal, recommendation_category
from app.db.models import CostRecord, Recommendation
from app.services.account_service import require_account
from app.services.cost_findings import findings_from_stored_costs
from app.services.mock_loader import load_json

SAVINGS_LABEL = "Estimated potential savings"
POTENTIAL_STATUSES = ("OPEN", "REVIEWED")


def _summary(evidence: dict | None) -> str:
    if not isinstance(evidence, dict):
        return "No evidence summary was recorded."
    summary = evidence.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return "No evidence summary was recorded."


def _assumptions(evidence: dict | None) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    assumptions = evidence.get("assumptions")
    if not isinstance(assumptions, list):
        return []
    return [item.strip() for item in assumptions if isinstance(item, str) and item.strip()]


def _currency(session: Session, account_id: int) -> str:
    currency = session.query(CostRecord.currency).filter(CostRecord.account_id == account_id).limit(1).scalar()
    return currency or "INR"


def list_recommendations(session: Session) -> dict:
    account = require_account(session)
    rows = (
        session.query(Recommendation)
        .filter(Recommendation.account_id == account.id)
        .order_by(Recommendation.priority, Recommendation.id)
        .all()
    )
    recommendations = []
    for row in rows:
        recommendations.append(
            {
                "id": row.id,
                "resource_id": row.resource_id,
                "title": row.title,
                "description": row.description,
                "service": row.service,
                "category": recommendation_category(row.action_type, row.risk_level),
                "current_monthly_cost": float(as_decimal(row.current_monthly_cost)),
                "estimated_monthly_savings": float(as_decimal(row.estimated_monthly_savings)),
                "estimated_annual_savings": float(as_decimal(row.estimated_annual_savings)),
                "confidence": row.confidence,
                "data_quality": row.data_quality,
                "risk_level": row.risk_level,
                "priority": row.priority,
                "action_type": row.action_type,
                "source": row.source,
                "status": row.status,
                "evidence_summary": _summary(row.evidence_json),
                "assumptions": _assumptions(row.evidence_json),
            }
        )
    if not recommendations:
        recommendations = findings_from_stored_costs(session, account.id)
    return {"currency": _currency(session, account.id), "recommendations": recommendations}


def get_savings(session: Session) -> dict:
    account = require_account(session)
    rows = (
        session.query(Recommendation)
        .filter(
            Recommendation.account_id == account.id,
            Recommendation.status.in_(POTENTIAL_STATUSES),
        )
        .all()
    )
    buckets = {"safe": as_decimal(0), "review": as_decimal(0), "architecture": as_decimal(0)}
    monthly = as_decimal(0)
    annual = as_decimal(0)
    for row in rows:
        category = recommendation_category(row.action_type, row.risk_level)
        amount = as_decimal(row.estimated_monthly_savings)
        buckets[category] = buckets[category] + amount
        monthly += amount
        annual += as_decimal(row.estimated_annual_savings)
    if not rows:
        findings = findings_from_stored_costs(session, account.id)
        for item in findings:
            category = item["category"]
            amount = as_decimal(item["estimated_monthly_savings"])
            buckets[category] = buckets[category] + amount
            monthly += amount
            annual += as_decimal(item["estimated_annual_savings"])
        label = (
            "Estimated potential savings. Upper bound if the listed usage is removed."
            if monthly
            else "No recommendations collected yet."
        )
    else:
        label = SAVINGS_LABEL
    return {
        "currency": _currency(session, account.id),
        "label": label,
        "potential_monthly_savings": float(monthly),
        "potential_annual_savings": float(annual),
        "safe_monthly_savings": float(buckets["safe"]),
        "review_monthly_savings": float(buckets["review"]),
        "architecture_monthly_savings": float(buckets["architecture"]),
    }


def get_optimization_score(session: Session) -> dict:
    require_account(session)
    if not get_settings().mock_aws:
        return {
            "score": None,
            "maximum": 100,
            "source": "unavailable",
            "label": "Not calculated",
        }
    payload = load_json("costs", "costs.json")
    score = int(payload["optimization_score"])
    if not 0 <= score <= 100:
        raise FinOpsError("Optimization score in the demo dataset is outside 0-100.", status_code=500)
    return {
        "score": score,
        "maximum": 100,
        "source": "demo_dataset",
        "label": "Optimization score",
    }
