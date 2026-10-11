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

UPPER_BOUND = (
    "Estimated potential savings equals this full-month charge if the design changes and this usage stops. "
    "Utilization was not measured, so this is an upper bound, not a guaranteed saving. Nothing has been removed."
)
NO_SAVING = (
    "No saving is estimated. Utilization was not measured, so this line is an investigation, not a quote."
)

# token, title, service, client brief, question for the client, architect steps.
# Briefs and steps may use {period}, {amount}, and {usage}. Amounts come from Cost Explorer.
ARCHITECTURE_PATTERNS = (
    (
        "NatGateway-Hours",
        "NAT Gateway hours",
        "EC2",
        "{period} NAT Gateway hours were {amount}. A NAT gateway is billed for every hour it exists, whether or not traffic flows. "
        "Use {amount} as the ceiling if a gateway is retired after private subnets have another outbound path. "
        "Do not tell the client this money is already saved.",
        "Which private subnets still need this NAT, and is there another outbound path?",
        (
            "List each NAT gateway, its subnet, and every route table whose default route targets it.",
            "Read BytesOutToDestination and ActiveConnectionCount for 14 days. A quiet gateway is the evidence for a retirement conversation. The cost line alone is not.",
            "If the only destinations are S3 or DynamoDB, compare a gateway VPC endpoint with keeping the NAT. A gateway endpoint has no hourly charge.",
            "Point routes at the replacement and confirm private workloads still connect. Delete the gateway only after that check.",
        ),
    ),
    (
        "TransitGateway-Hours",
        "Transit Gateway hours",
        "VPC",
        "{period} Transit Gateway attachment hours were {amount}. Each attachment is billed per hour even when it carries no traffic. "
        "Use {amount} as the ceiling if an attachment is removed after its routes have a replacement. Do not present it as money already saved.",
        "Which VPCs, VPNs, or accounts still depend on this attachment?",
        (
            "List attachments and the route tables on both sides that advertise them.",
            "In Cost Explorer, separate this hourly attachment charge from Transit Gateway data-processing charges before you quote a number.",
            "For two VPCs with little traffic, price VPC peering against the attachment hour charge. Peering has no hourly attachment fee.",
            "Move the routes first. Remove the attachment only after both sides no longer send traffic through it.",
        ),
    ),
    (
        "PublicIPv4:InUseAddress",
        "Public IPv4 addresses",
        "VPC",
        "{period} in-use public IPv4 addresses cost {amount}. Each in-use public IPv4 address is billed by the hour. "
        "Use {amount} as the ceiling if those addresses are released. Releasing an address that an instance, load balancer, or NAT still uses will break reachability.",
        "Which of these addresses are still the public name or IP that users and partners call?",
        (
            "List Elastic IPs and in-use public IPv4 addresses, and note the instance, NAT, load balancer, or network interface that holds each one.",
            "Split addresses that are attached from any that are allocated and idle. Idle addresses are the first release candidates.",
            "For instances that only need outbound access, check whether a private address behind NAT, or IPv6, replaces their own public address.",
            "Release an address only after DNS and security groups no longer point at it.",
        ),
    ),
    (
        "VpcEndpoint-Hours",
        "VPC endpoint hours",
        "VPC",
        "{period} interface VPC endpoint hours were {amount}. Interface endpoints are billed per hour in each Availability Zone, plus data processed. "
        "Use {amount} as the ceiling if an endpoint, or an extra Availability Zone, is removed after callers have another path. "
        "S3 and DynamoDB can use a gateway endpoint, which has no hourly charge.",
        "Which applications call this endpoint, and does it cover more Availability Zones than those applications use?",
        (
            "List interface endpoints, the AWS service each one fronts, and the Availability Zones enabled on it.",
            "For S3 or DynamoDB, check whether a gateway endpoint already exists. A gateway endpoint replaces the hourly interface charge for those two services.",
            "Confirm the security groups and applications that call the endpoint before you drop an Availability Zone or the endpoint.",
            "Remove unused Availability Zone coverage first. That cuts the hourly charge without removing the service.",
        ),
    ),
    (
        "ProtocolHours",
        "Transfer Family protocol hours",
        "Transfer",
        "{period} Transfer Family protocol hours were {amount}. The server is billed for each hour a protocol stays enabled, whether or not files move. "
        "Use {amount} as the ceiling if the server is stopped outside its transfer window, or the protocol is turned off. Confirm partners still need it before you quote that figure.",
        "Do partners still upload on this server, and do they need it running all month?",
        (
            "Identify the server, the enabled protocols, and the users or connectors that still sign in.",
            "Compare this protocol-hour line with the data-transfer line for the same month. Hours with almost no data are a scheduling change, not a deletion.",
            "If transfers happen in a window, stop the server outside that window.",
            "Turn a protocol off only after the partner has another way to exchange files.",
        ),
    ),
    (
        "WorkMail",
        "WorkMail user hours",
        "WorkMail",
        "{period} WorkMail user hours were {amount}. Mailboxes are billed per user-hour while they exist. "
        "Use {amount} as the ceiling if unused mailboxes are disabled. Disabling a mailbox removes that person's access.",
        "Which mailboxes had no sign-in, and is the client ready to disable them?",
        (
            "Export the mailbox list and mark users who have not signed in.",
            "Disable unused mailboxes. Do not delete them until the client agrees the retention window.",
            "Recount billable users and compare next month's WorkMail line with this {amount} charge.",
        ),
    ),
)

REVIEW_PATTERNS = (
    (
        "InstanceUsageIOOptimized:",
        "IO-optimized database hours",
        "RDS",
        "{period} {usage} cost {amount}. IO-optimized is a storage configuration, not proof the database is idle. "
        "No saving is quoted until you compare this charge with the I/O the cluster actually generates.",
        "Is this cluster's I/O volume high enough to justify IO-optimized, or was it left on by default?",
        (
            "Identify which clusters have the IO-optimized storage configuration enabled.",
            "In Cost Explorer, set this line next to Aurora storage I/O for the same month. The comparison is the decision, not this charge by itself.",
            "Switch the configuration only when the I/O volume does not justify it, and only on one cluster at a time.",
        ),
    ),
    (
        "BoxUsage:",
        "EC2 instance hours",
        "EC2",
        "{period} {usage} cost {amount}. These are compute hours for that instance type. "
        "No saving is quoted yet, because CPU, memory, and network were not measured. Bring a 14-day utilization chart before you propose a smaller size or a stop schedule.",
        "What does each instance of this type run, and can any of them stop outside business hours?",
        (
            "List running instances of this type and name the application on each one.",
            "Pull 14 days of CPU, network, and memory where an agent is installed. A smaller size without that chart is a guess.",
            "If utilization stays low and the workload allows it, price the next option from the AWS price list: a smaller size, a stop schedule, or Graviton. Do not invent the new monthly cost.",
            "Change one instance, watch the application, then repeat. Do not resize the fleet from this cost line alone.",
        ),
    ),
    (
        "InstanceUsage:",
        "Database instance hours",
        "RDS",
        "{period} {usage} cost {amount}. These are database instance hours. "
        "No saving is quoted yet, because CPU, connections, and I/O were not measured. A smaller class is a client proposal only after that chart exists.",
        "Which application uses this database, and what is the agreed maintenance window for a class change?",
        (
            "List instances of this class and the application and environment each one serves.",
            "Pull 14 days of CPU, database connections, and read/write I/O. Rightsizing without that chart is a guess.",
            "If the chart stays low, price one smaller class from the AWS price list and include the failover impact. Do not invent the new monthly cost.",
            "Change one instance in the maintenance window, confirm the application, then decide on the rest.",
        ),
    ),
    (
        "EBS:VolumeUsage",
        "EBS volume storage",
        "EBS",
        "{period} {usage} cost {amount}. This is disk capacity, not proof the disks are full or attached. "
        "No saving is quoted until you separate unattached volumes from volumes that are in use.",
        "Which of these volumes are attached to a running instance, and which are left over?",
        (
            "List volumes of this type. Mark state available versus in-use, and the instance each in-use volume is on.",
            "Unattached volumes are the first client conversation. Do not delete a volume that is attached.",
            "If the volume type is gp2, price gp3 at the same size from the AWS price list before you recommend a migration. If it is already gp3, the only saving is unused capacity, not a type change. Do not invent the difference.",
            "Snapshot a volume before you delete it, and confirm nothing boots from it.",
        ),
    ),
    (
        "EBS:SnapshotUsage",
        "EBS snapshot storage",
        "EBS",
        "{period} {usage} cost {amount}. Snapshots are retained backups. "
        "No saving is quoted until you know which snapshots are older than the client's retention rule and which AMIs still use them.",
        "How many days of snapshots does the client actually need to keep?",
        (
            "List snapshots, their age, and any AMI that still references them.",
            "Agree a retention window with the client before you delete anything.",
            "Delete only snapshots past that window and not referenced by an AMI. Keep the ones inside the window.",
        ),
    ),
    (
        "LoadBalancerUsage",
        "Load balancer hours",
        "ELB",
        "{period} {usage} cost {amount}. A load balancer is billed for every hour it exists. "
        "No saving is quoted until you know whether it still has targets and requests.",
        "Does this load balancer still receive traffic, or was it left behind by an old release?",
        (
            "List load balancers of this type, their listeners, and their target groups.",
            "Read RequestCount and healthy-host count for 14 days. Zero requests and no healthy targets are the retirement case.",
            "Confirm DNS no longer points at it, then delete it. Do not delete one that still fronts production.",
        ),
    ),
    (
        "CPUCredits:",
        "Burstable CPU credits",
        "EC2",
        "{period} {usage} cost {amount}. Credit charges mean a burstable instance spent beyond its baseline. "
        "No saving is quoted until you see whether the credit balance is exhausted or sitting unused.",
        "Is this instance bursting because it is too small, or are unlimited credits left on by default?",
        (
            "Find the instances of this family and read CPUCreditBalance and CPUSurplusCreditsCharged for 14 days.",
            "A balance that stays at zero means the size is too small. Price the next size from the AWS price list before you recommend it.",
            "A balance that stays high, with surplus charges, means unlimited mode may be an accidental setting. Confirm the workload before you turn it off.",
        ),
    ),
    (
        "Aurora:StorageIOUsage",
        "Aurora storage I/O",
        "RDS",
        "{period} {usage} cost {amount}. This is I/O, not instance hours. "
        "No saving is quoted from deleting the database. The architect decision is whether IO-optimized storage costs less than this I/O line.",
        "Is this I/O steady enough that IO-optimized storage would cost less than standard I/O?",
        (
            "Set this I/O line next to any IO-optimized storage charge for the same cluster and month.",
            "Price IO-optimized for this cluster from the AWS price list. Use that quote, not a guessed percentage.",
            "Switch one cluster, compare the next month, then decide on the others.",
        ),
    ),
    (
        "Aurora:BackupUsage",
        "Aurora backup storage",
        "RDS",
        "{period} {usage} cost {amount}. Backup storage above the included retention is a retention choice. "
        "No saving is quoted until the client agrees how many days they can restore.",
        "How many days of restore does the client need, and are extra snapshot copies still required?",
        (
            "Read the backup retention on each cluster and list manual snapshots and cross-region copies.",
            "Agree the restore window with the client before you shorten retention.",
            "Remove manual snapshots and copies outside that window. Leave automated backups inside it.",
        ),
    ),
)


def _match(usage_type: str) -> tuple[str, str, str, str, str, tuple[str, ...]] | None:
    for token, title, service, brief, ask, steps in ARCHITECTURE_PATTERNS:
        if token in usage_type:
            return "ARCHITECTURE", _title(title, usage_type, token), service, brief, ask, steps
    for token, title, service, brief, ask, steps in REVIEW_PATTERNS:
        if token in usage_type:
            return "REVIEW", _title(title, usage_type, token), service, brief, ask, steps
    return None


def _title(title: str, usage_type: str, token: str) -> str:
    before, _separator, after = usage_type.partition(token)
    detail = " ".join(part.strip("-:.") for part in (before, after) if part.strip("-:."))
    if detail:
        return f"{title} — {detail}"
    return title


def _fill(template: str, period_label: str, amount: Decimal, currency: str, usage_type: str) -> str:
    return template.format(
        period=period_label,
        amount=f"{amount:,.2f} {currency}",
        usage=usage_type,
    )


def build_cost_findings(
    rows: list[tuple[str, str, Decimal]],
    period_label: str,
    currency: str = "USD",
) -> list[dict]:
    matched: list[tuple] = []
    for service_name, usage_type, amount in rows:
        amount = as_decimal(amount)
        if amount < MINIMUM_MONTHLY_COST:
            continue
        found = _match(usage_type)
        if found is None:
            continue
        action_type, title, service, brief, ask, steps = found
        matched.append((amount, usage_type, action_type, title, service or service_name, brief, ask, steps))
    matched.sort(key=lambda item: item[0], reverse=True)
    architecture = [item for item in matched if item[2] == "ARCHITECTURE"]
    review = [item for item in matched if item[2] == "REVIEW"][:REVIEW_LIMIT]
    selected = architecture + review
    findings = []
    for index, (amount, usage_type, action_type, title, service, brief, ask, steps) in enumerate(selected, start=1):
        estimated = amount if action_type == "ARCHITECTURE" else as_decimal(0)
        values = (period_label, amount, currency, usage_type)
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
                    f"{amount:.2f} {currency}. A partial later month was not used as the basis."
                ),
                "assumptions": [UPPER_BOUND if action_type == "ARCHITECTURE" else NO_SAVING],
                "client_brief": _fill(brief, *values),
                "client_ask": ask,
                "next_steps": [_fill(step, *values) for step in steps],
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
    currency = session.query(CostRecord.currency).filter(CostRecord.account_id == account_id).limit(1).scalar()
    return build_cost_findings(usage, _period_label(basis), currency or "USD")
