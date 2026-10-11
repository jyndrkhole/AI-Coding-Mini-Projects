"""Store and read normalized inventory."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import FinOpsError
from app.core.money import as_decimal
from app.db.models import Metric, Recommendation, Resource
from app.services.account_service import require_account

GENERATED_SOURCES = ("INTERNAL_RULE", "COMPUTE_OPTIMIZER", "COST_OPTIMIZATION_HUB", "COST_EXPLORER")


def replace_inventory(session: Session, account_id: int, resources: list[dict], metrics: list[dict]) -> None:
    existing = session.query(Resource).filter(Resource.account_id == account_id).all()
    if existing:
        ids = [row.id for row in existing]
        session.query(Metric).filter(Metric.resource_id.in_(ids)).delete(synchronize_session=False)
        session.query(Resource).filter(Resource.account_id == account_id).delete(synchronize_session=False)
        session.flush()
    by_aws_id: dict[str, Resource] = {}
    for item in resources:
        if not item.get("resource_id"):
            continue
        row = Resource(
            account_id=account_id,
            resource_id=item["resource_id"],
            resource_type=item.get("resource_type") or "resource",
            service=item.get("service") or "",
            region=item.get("region") or "",
            name=item.get("name"),
            state=item.get("state"),
            instance_type=item.get("instance_type"),
            environment=item.get("environment"),
            tags_json=item.get("tags") or {},
            metadata_json=item.get("metadata") or {},
        )
        session.add(row)
        by_aws_id[item["resource_id"]] = row
    session.flush()
    for item in metrics:
        resource = by_aws_id.get(item.get("resource_id"))
        if resource is None:
            continue
        session.add(
            Metric(
                resource_id=resource.id,
                metric_name=item["metric_name"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                period=int(item.get("period") or 86400),
                average=as_decimal(item["average"]) if item.get("average") is not None else None,
                minimum=as_decimal(item["minimum"]) if item.get("minimum") is not None else None,
                maximum=as_decimal(item["maximum"]) if item.get("maximum") is not None else None,
                sample_count=item.get("sample_count"),
            )
        )


def replace_generated_recommendations(session: Session, account_id: int, rows: list[dict]) -> None:
    session.query(Recommendation).filter(
        Recommendation.account_id == account_id,
        Recommendation.source.in_(GENERATED_SOURCES),
    ).delete(synchronize_session=False)
    for item in rows:
        monthly = as_decimal(item.get("estimated_monthly_savings"))
        annual = as_decimal(item.get("estimated_annual_savings"))
        if annual != (monthly * 12).quantize(Decimal("0.01")):
            annual = (monthly * 12).quantize(Decimal("0.01"))
        session.add(
            Recommendation(
                account_id=account_id,
                resource_id=item.get("resource_id"),
                rule_id=item.get("rule_id"),
                source=item["source"],
                service=item.get("service") or "",
                title=item["title"],
                description=item["description"],
                evidence_json=item.get("evidence") or {},
                current_monthly_cost=as_decimal(item.get("current_monthly_cost")),
                estimated_monthly_savings=monthly,
                estimated_annual_savings=annual,
                confidence=item.get("confidence") or "LOW",
                data_quality=item.get("data_quality") or "PARTIAL",
                risk_level=item.get("risk_level") or "MEDIUM",
                priority=int(item.get("priority") or 100),
                action_type=item.get("action_type") or "REVIEW",
                status=item.get("status") or "OPEN",
            )
        )


def resource_views(session: Session, account_id: int) -> list[dict]:
    rows = session.query(Resource).filter(Resource.account_id == account_id).all()
    views = []
    for row in rows:
        metrics = {}
        for metric in session.query(Metric).filter(Metric.resource_id == row.id).all():
            metrics[metric.metric_name] = {
                "average": float(metric.average) if metric.average is not None else None,
                "minimum": float(metric.minimum) if metric.minimum is not None else None,
                "maximum": float(metric.maximum) if metric.maximum is not None else None,
                "sample_count": metric.sample_count,
            }
        views.append(
            {
                "resource_id": row.resource_id,
                "resource_type": row.resource_type,
                "service": row.service,
                "region": row.region,
                "name": row.name,
                "state": row.state,
                "instance_type": row.instance_type,
                "environment": row.environment,
                "tags": row.tags_json or {},
                "metadata": row.metadata_json or {},
                "metrics": metrics,
            }
        )
    return views


def list_resources(session: Session, service: str | None, region: str | None, environment: str | None, state: str | None, tag: str | None) -> dict:
    account = require_account(session)
    rows = session.query(Resource).filter(Resource.account_id == account.id).order_by(Resource.service, Resource.resource_id).all()
    items = []
    for row in rows:
        if service and row.service != service:
            continue
        if region and row.region != region:
            continue
        if environment and (row.environment or "") != environment:
            continue
        if state and (row.state or "") != state:
            continue
        if tag and tag not in (row.tags_json or {}):
            continue
        items.append(_resource_payload(session, row, include_metrics=False))
    return {"resources": items}


def get_resource(session: Session, resource_id: str) -> dict:
    account = require_account(session)
    row = session.query(Resource).filter(Resource.account_id == account.id, Resource.resource_id == resource_id).one_or_none()
    if row is None:
        raise FinOpsError("Resource was not found.", status_code=404)
    return _resource_payload(session, row, include_metrics=True)


def _resource_payload(session: Session, row: Resource, include_metrics: bool) -> dict:
    payload = {
        "id": row.id,
        "resource_id": row.resource_id,
        "resource_type": row.resource_type,
        "service": row.service,
        "region": row.region,
        "name": row.name,
        "state": row.state,
        "instance_type": row.instance_type,
        "environment": row.environment,
        "tags": row.tags_json or {},
        "metadata": row.metadata_json or {},
    }
    if include_metrics:
        metrics = session.query(Metric).filter(Metric.resource_id == row.id).all()
        payload["metrics"] = [
            {
                "metric_name": metric.metric_name,
                "timestamp": metric.timestamp.isoformat() if metric.timestamp else None,
                "period": metric.period,
                "average": float(metric.average) if metric.average is not None else None,
                "minimum": float(metric.minimum) if metric.minimum is not None else None,
                "maximum": float(metric.maximum) if metric.maximum is not None else None,
                "sample_count": metric.sample_count,
            }
            for metric in metrics
        ]
    return payload
