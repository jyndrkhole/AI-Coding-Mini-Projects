"""Turn stored Cost Explorer usage into review findings. Savings are upper bounds, not measured idle time."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import as_decimal, recommendation_category
from app.db.models import CostRecord
from app.services.cost_service import (
    _as_date,
    _current_month,
    _latest_daily,
    _next_month,
    _period_label,
    _previous_month,
)

MINIMUM_MONTHLY_COST = Decimal("50")
REVIEW_LIMIT = 8

ARCHITECTURE_PATTERNS = (
    ("NatGateway-Hours", "NAT Gateway hours", "EC2"),
    ("TransitGateway-Hours", "Transit Gateway hours", "VPC"),
    ("PublicIPv4:InUseAddress", "Public IPv4 addresses", "VPC"),
    ("VpcEndpoint-Hours", "VPC endpoint hours", "VPC"),
    ("ProtocolHours", "Transfer Family protocol hours", "Transfer"),
    ("WorkMail", "WorkMail user hours", "WorkMail"),
)
REVIEW_PATTERNS = (
    ("InstanceUsageIOOptimized:", "IO-optimized database hours", "RDS"),
    ("BoxUsage:", "EC2 instance hours", "EC2"),
    ("InstanceUsage:", "Database instance hours", "RDS"),
    ("EBS:VolumeUsage", "EBS volume storage", "EBS"),
    ("EBS:SnapshotUsage", "EBS snapshot storage", "EBS"),
    ("LoadBalancerUsage", "Load balancer hours", "ELB"),
    ("CPUCredits:", "Burstable CPU credits", "EC2"),
    ("Aurora:StorageIOUsage", "Aurora storage I/O", "RDS"),
    ("Aurora:BackupUsage", "Aurora backup storage", "RDS"),
)

UPPER_BOUND = (
    "Estimated potential savings equals this full-month charge if the usage is removed. "
    "Utilization was not measured, so this is an upper bound, not a guaranteed saving."
)
NO_SAVING = "No saving is estimated. Utilization was not measured."


def _match(usage_type: str) -> tuple[str, str, str] | None:
    for token, title, service in ARCHITECTURE_PATTERNS:
        if token in usage_type:
            return "ARCHITECTURE", title, service
    for token, title, service in REVIEW_PATTERNS:
        if token in usage_type:
            return "REVIEW", title, service
    return None


def build_cost_findings(rows: list[tuple[str, str, Decimal]], period_label: str) -> list[dict]:
    matched: list[tuple[Decimal, str, str, str, str]] = []
    for service_name, usage_type, amount in rows:
        amount = as_decimal(amount)
        if amount < MINIMUM_MONTHLY_COST:
            continue
        found = _match(usage_type)
        if found is None:
            continue
        action_type, title, service = found
        matched.append((amount, usage_type, action_type, title, service or service_name))
    matched.sort(key=lambda item: item[0], reverse=True)
    architecture = [item for item in matched if item[2] == "ARCHITECTURE"]
    review = [item for item in matched if item[2] == "REVIEW"][:REVIEW_LIMIT]
    selected = architecture + review
    findings = []
    for index, (amount, usage_type, action_type, title, service) in enumerate(selected, start=1):
        estimated = amount if action_type == "ARCHITECTURE" else as_decimal(0)
        findings.append(
            {
                "id": index,
                "resource_id": usage_type,
                "title": title,
                "description": f"{period_label} unblended cost for {usage_type}.",
                "service": service,
                "category": recommendation_category(action_type, "MEDIUM"),
                "current_monthly_cost": float(amount),
                "estimated_monthly_savings": float(estimated),
                "estimated_annual_savings": float(estimated * 12),
                "confidence": "LOW",
                "data_quality": "COST_ONLY",
                "risk_level": "MEDIUM",
                "priority": index,
                "action_type": action_type,
                "source": "COST_EXPLORER",
                "status": "OPEN",
                "evidence_summary": (
                    f"{period_label} unblended Cost Explorer cost for {usage_type} was "
                    f"{amount:.2f}. A partial later month was not used as the basis."
                ),
                "assumptions": [UPPER_BOUND if action_type == "ARCHITECTURE" else NO_SAVING],
            }
        )
    return findings


def findings_from_stored_costs(session: Session, account_id: int) -> list[dict]:
    current = _current_month(session, account_id)
    latest = _latest_daily(session, account_id)
    basis = _previous_month(current) if latest < _next_month(current) - timedelta(days=1) else current
    rows = (
        session.query(CostRecord)
        .filter(
            CostRecord.account_id == account_id,
            CostRecord.source == "usage",
            CostRecord.date >= basis,
            CostRecord.date < _next_month(basis),
        )
        .all()
    )
    usage = [
        (row.service, row.usage_type, as_decimal(row.amount))
        for row in rows
        if row.usage_type
    ]
    return build_cost_findings(usage, _period_label(basis))
