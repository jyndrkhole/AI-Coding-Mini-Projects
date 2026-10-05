"""Load the demo account into the database when mock mode is on."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.money import as_decimal
from app.db.database import get_sessionmaker
from app.db.models import Account, Metric, Recommendation, Resource
from app.services.cost_store import CostLine, replace_cost_records
from app.services.mock_loader import load_json

logger = get_logger(__name__)

RESOURCE_FILES = (
    "resources/ec2.json",
    "resources/ebs.json",
    "resources/rds.json",
    "resources/s3.json",
    "resources/lambda.json",
    "resources/nat.json",
)


def _month_total(rows: list[dict], month: str) -> Decimal:
    return sum((as_decimal(row["amount"]) for row in rows if row["month"] == month), Decimal("0.00"))


def _require_balanced(costs: dict) -> None:
    current = costs["current_month"]
    previous = costs["previous_month"]
    daily = sum((as_decimal(row["amount"]) for row in costs["daily"]), Decimal("0.00"))
    current_services = _month_total(costs["services"], current)
    current_regions = _month_total(costs["regions"], current)
    previous_services = _month_total(costs["services"], previous)
    previous_regions = _month_total(costs["regions"], previous)
    if daily != current_services or daily != current_regions:
        raise ValueError("Demo current-month daily, service, and region totals do not match.")
    if previous_services != previous_regions:
        raise ValueError("Demo previous-month service and region totals do not match.")
    current_usage = _month_total(costs["usage"], current)
    previous_usage = _month_total(costs["usage"], previous)
    if current_usage != current_services or previous_usage != previous_services:
        raise ValueError("Demo usage totals do not match service totals.")
    expected = as_decimal(costs["current_month_total"])
    previous_expected = as_decimal(costs["previous_month_total"])
    if daily != expected or previous_services != previous_expected:
        raise ValueError("Demo cost totals do not match the declared month totals.")


def seed_mock_data() -> None:
    costs = load_json("costs", "costs.json")
    _require_balanced(costs)
    account_payload = costs["account"]
    session = get_sessionmaker()()
    try:
        existing = session.query(Account).filter_by(aws_account_id=account_payload["aws_account_id"]).one_or_none()
        if existing is None:
            _insert_demo(session, costs)
        else:
            replace_cost_records(session, existing.id, demo_cost_lines(costs))
        session.commit()
        logger.info("Loaded demo cost data for account %s", account_payload["aws_account_id"])
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def demo_cost_lines(costs: dict) -> list[CostLine]:
    currency = costs["currency"]
    lines: list[CostLine] = []
    for point in costs["daily"]:
        lines.append(
            CostLine(
                date=datetime.fromisoformat(point["date"]).date(),
                service="all",
                region="all",
                usage_type="",
                amount=as_decimal(point["amount"]),
                currency=currency,
                source="daily",
            )
        )
    for row in costs["services"]:
        lines.append(
            CostLine(
                date=datetime.fromisoformat(f"{row['month']}-01").date(),
                service=row["service"],
                region="all",
                usage_type="",
                amount=as_decimal(row["amount"]),
                currency=currency,
                source="service",
            )
        )
    for row in costs["regions"]:
        lines.append(
            CostLine(
                date=datetime.fromisoformat(f"{row['month']}-01").date(),
                service="all",
                region=row["region"],
                usage_type="",
                amount=as_decimal(row["amount"]),
                currency=currency,
                source="region",
            )
        )
    for row in costs["usage"]:
        lines.append(
            CostLine(
                date=datetime.fromisoformat(f"{row['month']}-01").date(),
                service=row["service"],
                region="all",
                usage_type=row["usage_type"],
                amount=as_decimal(row["amount"]),
                currency=currency,
                source="usage",
            )
        )
    return lines


def _insert_demo(session: Session, costs: dict) -> None:
    account_payload = costs["account"]
    account = Account(
        aws_account_id=account_payload["aws_account_id"],
        account_alias=account_payload["account_alias"],
        region=account_payload["region"],
        role_arn=account_payload["role_arn"],
        last_scan_at=datetime.fromisoformat(account_payload["last_scan_at"]),
    )
    session.add(account)
    session.flush()

    replace_cost_records(session, account.id, demo_cost_lines(costs))

    resources_by_aws_id: dict[str, Resource] = {}
    for relative in RESOURCE_FILES:
        folder, name = relative.split("/")
        payload = load_json(folder, name)
        for item in payload["resources"]:
            resource = Resource(
                account_id=account.id,
                resource_id=item["resource_id"],
                resource_type=item["resource_type"],
                service=item["service"],
                region=item["region"],
                name=item.get("name"),
                state=item.get("state"),
                instance_type=item.get("instance_type"),
                environment=item.get("environment"),
                tags_json=item.get("tags") or {},
                metadata_json=item.get("metadata") or {},
            )
            session.add(resource)
            resources_by_aws_id[item["resource_id"]] = resource
    session.flush()

    metrics = load_json("metrics", "metrics.json")
    for item in metrics["metrics"]:
        resource = resources_by_aws_id.get(item["resource_id"])
        if resource is None:
            raise ValueError(f"Metric refers to unknown resource {item['resource_id']}")
        session.add(
            Metric(
                resource_id=resource.id,
                metric_name=item["metric_name"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                period=item["period"],
                average=as_decimal(item["average"]) if item.get("average") is not None else None,
                minimum=as_decimal(item["minimum"]) if item.get("minimum") is not None else None,
                maximum=as_decimal(item["maximum"]) if item.get("maximum") is not None else None,
                sample_count=item.get("sample_count"),
            )
        )

    recommendations = load_json("recommendations", "demo.json")
    for item in recommendations["recommendations"]:
        monthly = as_decimal(item["estimated_monthly_savings"])
        annual = as_decimal(item["estimated_annual_savings"])
        if annual != (monthly * 12).quantize(Decimal("0.01")):
            raise ValueError(f"Annual savings do not equal monthly x 12 for {item['title']}")
        session.add(
            Recommendation(
                account_id=account.id,
                resource_id=item.get("resource_id"),
                rule_id=item.get("rule_id"),
                source=item["source"],
                service=item["service"],
                title=item["title"],
                description=item["description"],
                evidence_json=item["evidence"],
                current_monthly_cost=as_decimal(item["current_monthly_cost"]),
                estimated_monthly_savings=monthly,
                estimated_annual_savings=annual,
                confidence=item["confidence"],
                data_quality=item["data_quality"],
                risk_level=item["risk_level"],
                priority=item["priority"],
                action_type=item["action_type"],
                status=item.get("status", "OPEN"),
            )
        )
