"""What-if schedule estimate. The current cost must already be stored on a resource or recommendation."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import FinOpsError
from app.core.money import as_decimal
from app.db.models import Recommendation, Resource, Simulation
from app.services.account_service import require_account

WEEK_HOURS = Decimal("168")


def run_simulation(session: Session, scenario_type: str, hours_per_weekday: int, environment: str) -> dict:
    if scenario_type != "business_hours":
        raise FinOpsError("This scenario is not supported yet.", status_code=400)
    if hours_per_weekday < 1 or hours_per_weekday > 24:
        raise FinOpsError("Hours per weekday must be between 1 and 24.", status_code=400)
    account = require_account(session)
    target = environment.strip().lower()
    if target not in {"dev", "development"}:
        raise FinOpsError("Schedule simulation currently applies to dev or development instances.", status_code=400)

    instances = (
        session.query(Resource)
        .filter(Resource.account_id == account.id, Resource.service == "EC2", Resource.resource_type == "instance")
        .all()
    )
    selected = [row for row in instances if str(row.environment or "").lower() == target and row.state == "running"]
    included = []
    excluded = []
    current = Decimal("0.00")
    for row in selected:
        cost = _recorded_cost(session, account.id, row)
        if cost is None:
            excluded.append(row.resource_id)
            continue
        included.append(row.resource_id)
        current += cost
    running_hours = Decimal(hours_per_weekday * 5)
    if current == 0:
        projected = Decimal("0.00")
        savings = Decimal("0.00")
    else:
        projected = (current * running_hours / WEEK_HOURS).quantize(Decimal("0.01"))
        savings = (current - projected).quantize(Decimal("0.01"))
    assumptions = [
        "ESTIMATE. This assumes the included instances currently run 24 hours a day, 7 days a week.",
        f"The proposed schedule is {hours_per_weekday} hours a day on weekdays, which is {running_hours} of {WEEK_HOURS} hours.",
        "Instances without a stored monthly cost are excluded. Their cost was not invented.",
    ]
    if excluded:
        assumptions.append("Excluded because no monthly cost is stored: " + ", ".join(excluded))
    record = Simulation(
        account_id=account.id,
        name=f"{target} instances at {hours_per_weekday}h weekdays",
        scenario_type=scenario_type,
        input_json={"hours_per_weekday": hours_per_weekday, "environment": target, "resources": included},
        current_cost=current,
        projected_cost=projected,
        potential_savings=savings,
        assumptions_json={"assumptions": assumptions, "label": "ESTIMATE"},
        risk_level="LOW",
    )
    session.add(record)
    session.commit()
    return {
        "id": record.id,
        "label": "ESTIMATE",
        "scenario_type": scenario_type,
        "currency": _currency(session, account.id),
        "current_monthly_cost": float(current),
        "projected_monthly_cost": float(projected),
        "potential_monthly_savings": float(savings),
        "potential_annual_savings": float((savings * 12).quantize(Decimal("0.01"))),
        "included_resources": included,
        "excluded_resources": excluded,
        "assumptions": assumptions,
        "risk_level": "LOW",
    }


def _recorded_cost(session: Session, account_id: int, resource: Resource) -> Decimal | None:
    metadata = resource.metadata_json or {}
    if metadata.get("monthly_cost") is not None:
        return as_decimal(metadata["monthly_cost"])
    row = (
        session.query(Recommendation)
        .filter(
            Recommendation.account_id == account_id,
            Recommendation.resource_id == resource.resource_id,
            Recommendation.current_monthly_cost > 0,
        )
        .order_by(Recommendation.current_monthly_cost.desc())
        .first()
    )
    if row is None:
        return None
    return as_decimal(row.current_monthly_cost)


def _currency(session: Session, account_id: int) -> str:
    from app.db.models import CostRecord

    currency = session.query(CostRecord.currency).filter(CostRecord.account_id == account_id).limit(1).scalar()
    return currency or "USD"
