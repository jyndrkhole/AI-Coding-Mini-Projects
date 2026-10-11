"""Deterministic cost rules. Savings stay zero unless a stored cost is already on the resource."""

from datetime import date, datetime
from decimal import Decimal

from app.core.money import as_decimal

OLD_FAMILIES = ("t2.", "m4.", "m3.", "c4.", "c3.", "r4.", "r3.", "i2.")
DEV_ENVIRONMENTS = {"dev", "development"}
CPU_THRESHOLD = Decimal("10")
SNAPSHOT_AGE_DAYS = 90
HOURLY_SAMPLES_FOR_14_DAYS = 24 * 14


class CostRule:
    rule_id = ""
    name = ""
    service = ""
    description = ""

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        return []


class RuleRegistry:
    def __init__(self, rules: list[CostRule] | None = None) -> None:
        self.rules = rules if rules is not None else default_rules()

    def evaluate(self, resources: list[dict], today: date | None = None) -> list[dict]:
        today = today or date.today()
        found: list[dict] = []
        for resource in resources:
            for rule in self.rules:
                found.extend(rule.evaluate(resource, today))
        gap = tagging_gap(resources)
        if gap:
            found.append(gap)
        return _rank(found)


def default_rules() -> list[CostRule]:
    return [
        UnderutilizedEc2(),
        DevInstanceAlwaysOn(),
        OldInstanceGeneration(),
        UnattachedVolume(),
        Gp2Review(),
        OldSnapshot(),
        RdsUnderutilized(),
        S3MissingLifecycle(),
        NatArchitectureReview(),
        UnassociatedAddress(),
        TaggingGap(),
    ]


def _metric(resource: dict, name: str) -> dict | None:
    metrics = resource.get("metrics") or {}
    value = metrics.get(name)
    return value if isinstance(value, dict) else None


def _stored_cost(resource: dict) -> Decimal | None:
    metadata = resource.get("metadata") or {}
    if metadata.get("monthly_cost") is None:
        return None
    return as_decimal(metadata["monthly_cost"])


def _recommendation(
    rule: CostRule,
    resource: dict,
    title: str,
    description: str,
    risk: str,
    action: str,
    facts: list[str],
    assumptions: list[str],
    confidence: str = "LOW",
    data_quality: str = "PARTIAL",
    savings: Decimal | None = None,
) -> dict:
    monthly = as_decimal(savings) if savings is not None else Decimal("0.00")
    cost = _stored_cost(resource) or Decimal("0.00")
    return {
        "resource_id": resource.get("resource_id"),
        "rule_id": rule.rule_id,
        "source": "INTERNAL_RULE",
        "service": rule.service or resource.get("service") or "",
        "title": title,
        "description": description,
        "evidence": {
            "summary": description,
            "facts": facts,
            "assumptions": assumptions,
            "pricing_available": savings is not None and monthly > 0,
            "client_brief": description,
            "client_ask": assumptions[0] if assumptions else "",
            "next_steps": facts,
        },
        "current_monthly_cost": cost,
        "estimated_monthly_savings": monthly,
        "estimated_annual_savings": (monthly * 12).quantize(Decimal("0.01")),
        "confidence": confidence,
        "data_quality": data_quality,
        "risk_level": risk,
        "action_type": action,
        "status": "OPEN",
    }


class UnderutilizedEc2(CostRule):
    rule_id = "EC2-001"
    name = "UNDERUTILIZED_EC2"
    service = "EC2"
    description = "Low CPU is not enough to resize an instance."

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("service") != "EC2" or resource.get("resource_type") != "instance":
            return []
        cpu = _metric(resource, "CPUUtilization")
        if cpu is None or cpu.get("average") is None:
            return []
        average = as_decimal(cpu["average"])
        if average >= CPU_THRESHOLD:
            return []
        samples = cpu.get("sample_count") or 0
        memory = _metric(resource, "MemoryUtilization") or _metric(resource, "mem_used_percent")
        quality = "PARTIAL" if samples < HOURLY_SAMPLES_FOR_14_DAYS else "MEASURED"
        facts = [
            f"CPU average {average}%",
            f"CPU peak {cpu.get('maximum')}%" if cpu.get("maximum") is not None else "CPU peak was not stored",
            "Memory utilization was not collected" if memory is None else "Memory utilization is stored",
            f"Instance type {resource.get('instance_type') or 'unknown'}",
            f"Environment {resource.get('environment') or 'untagged'}",
        ]
        if samples < HOURLY_SAMPLES_FOR_14_DAYS:
            facts.append("Stored samples do not confirm a 14-day window.")
        description = (
            "CPU is below 10%. Additional validation required before any size change. "
            "Memory, disk, and the application on this instance were not used to estimate a saving."
        )
        return [
            _recommendation(
                self,
                resource,
                "Validate before resizing this instance",
                description,
                "MEDIUM",
                "REVIEW",
                facts,
                ["No saving is estimated from CPU alone."],
                confidence="LOW",
                data_quality=quality,
            )
        ]


class DevInstanceAlwaysOn(CostRule):
    rule_id = "EC2-002"
    name = "DEV_INSTANCE_RUNNING_24X7"
    service = "EC2"
    description = "Development instances that stay running are scheduling candidates."

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("service") != "EC2" or resource.get("resource_type") != "instance":
            return []
        environment = str(resource.get("environment") or "").lower()
        if environment not in DEV_ENVIRONMENTS or resource.get("state") != "running":
            return []
        schedule = (resource.get("metadata") or {}).get("schedule")
        if schedule not in (None, "", "none"):
            return []
        cost = _stored_cost(resource)
        assumptions = [
            "A business-hours schedule assumes the instance currently runs 24 hours a day and would run 12 hours on weekdays only (60 of 168 hours).",
        ]
        savings = None
        if cost is not None:
            savings = (cost * (Decimal("168") - Decimal("60")) / Decimal("168")).quantize(Decimal("0.01"))
            assumptions.append("The current monthly cost used here was stored on the resource. This is an estimate, not a guaranteed saving.")
        else:
            assumptions.append("No per-instance monthly cost is stored, so no saving is estimated.")
        return [
            _recommendation(
                self,
                resource,
                "Review a business-hours schedule",
                "This development instance is running without a schedule. Stopping it outside business hours is the lower-risk option. Do not resize it from this rule.",
                "LOW",
                "SCHEDULE",
                [f"Environment is {environment}", "State is running", "No schedule is recorded"],
                assumptions,
                confidence="MEDIUM" if cost is not None else "LOW",
                savings=savings,
            )
        ]


class OldInstanceGeneration(CostRule):
    rule_id = "EC2-003"
    name = "OLD_INSTANCE_GENERATION"
    service = "EC2"
    description = "Previous-generation families are review candidates, without a price claim."

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        instance_type = str(resource.get("instance_type") or "")
        if resource.get("service") != "EC2" or not instance_type.startswith(OLD_FAMILIES):
            return []
        return [
            _recommendation(
                self,
                resource,
                "Review migration to a current-generation equivalent",
                "Review migration to a current-generation equivalent. No saving is claimed because a current price for the replacement was not loaded.",
                "MEDIUM",
                "REVIEW",
                [f"Instance type {instance_type}"],
                ["Pricing data for a replacement type is not available."],
            )
        ]


class UnattachedVolume(CostRule):
    rule_id = "EBS-001"
    name = "UNATTACHED_VOLUME"
    service = "EBS"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("resource_type") != "volume" or resource.get("state") != "available":
            return []
        cost = _stored_cost(resource)
        size = (resource.get("metadata") or {}).get("size_gib")
        assumptions = ["Confirm ownership and take a snapshot before deleting an unattached volume."]
        if cost is None:
            assumptions.append("Storage price was not loaded, so no saving is estimated.")
        return [
            _recommendation(
                self,
                resource,
                "Review the unattached volume",
                "This volume appears unused based on the available evidence. Confirm ownership and dependencies before deletion.",
                "LOW",
                "CLEANUP",
                [f"State is available", f"Size is {size} GiB" if size is not None else "Size was not stored"],
                assumptions,
                confidence="MEDIUM",
                savings=cost,
            )
        ]


class Gp2Review(CostRule):
    rule_id = "EBS-002"
    name = "GP2_REVIEW"
    service = "EBS"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("resource_type") != "volume" or resource.get("instance_type") != "gp2":
            return []
        return [
            _recommendation(
                self,
                resource,
                "Review migration from gp2 to gp3",
                "Review migration to gp3 where appropriate. No saving is claimed without a price for this volume size.",
                "LOW",
                "REVIEW",
                ["Volume type is gp2"],
                ["A gp3 price was not loaded."],
            )
        ]


class OldSnapshot(CostRule):
    rule_id = "EBS-003"
    name = "OLD_SNAPSHOT"
    service = "EBS"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("resource_type") != "snapshot":
            return []
        started = (resource.get("metadata") or {}).get("started_at")
        if not started:
            return []
        try:
            started_on = datetime.fromisoformat(str(started)).date()
        except ValueError:
            return []
        age = (today - started_on).days
        if age < SNAPSHOT_AGE_DAYS:
            return []
        size = (resource.get("metadata") or {}).get("volume_size_gib")
        return [
            _recommendation(
                self,
                resource,
                "Review snapshot retention",
                "This snapshot is older than 90 days. Do not delete it until the client confirms retention and that no AMI depends on it.",
                "MEDIUM",
                "REVIEW",
                [f"Age is {age} days", f"Size is {size} GiB" if size is not None else "Size was not stored", "Retention policy was not collected"],
                ["Age alone is not a reason to delete a snapshot."],
            )
        ]


class RdsUnderutilized(CostRule):
    rule_id = "RDS-001"
    name = "RDS_UNDERUTILIZED"
    service = "RDS"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("service") != "RDS":
            return []
        cpu = _metric(resource, "CPUUtilization")
        if cpu is None or cpu.get("average") is None or as_decimal(cpu["average"]) >= CPU_THRESHOLD:
            return []
        return [
            _recommendation(
                self,
                resource,
                "Validate database size before a class change",
                "Database CPU is below 10%. Connections and I/O were not judged sufficient to quote a smaller class.",
                "MEDIUM",
                "REVIEW",
                [f"CPU average {cpu.get('average')}%", f"Class {resource.get('instance_type')}"],
                ["No saving is estimated without a stored price for a smaller class."],
            )
        ]


class S3MissingLifecycle(CostRule):
    rule_id = "S3-001"
    name = "MISSING_LIFECYCLE"
    service = "S3"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("service") != "S3":
            return []
        if (resource.get("metadata") or {}).get("lifecycle"):
            return []
        return [
            _recommendation(
                self,
                resource,
                "Review a lifecycle policy",
                "No lifecycle configuration was found. This is a storage-governance review, not a quoted saving.",
                "LOW",
                "REVIEW",
                ["Lifecycle configuration was not present", f"Versioning {(resource.get('metadata') or {}).get('versioning') or 'unknown'}"],
                ["Object counts and storage class mix were not collected, so no saving is estimated."],
            )
        ]


class NatArchitectureReview(CostRule):
    rule_id = "NAT-001"
    name = "NAT_ARCHITECTURE_REVIEW"
    service = "NAT Gateway"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("resource_type") != "nat_gateway":
            return []
        return [
            _recommendation(
                self,
                resource,
                "Architecture review required",
                "Architecture review required. Map the route tables and compare S3 or DynamoDB gateway endpoints before treating the NAT hour charge as a saving.",
                "MEDIUM",
                "ARCHITECTURE",
                [
                    f"VPC {(resource.get('metadata') or {}).get('vpc_id') or 'unknown'}",
                    f"Subnet {(resource.get('metadata') or {}).get('subnet_id') or 'unknown'}",
                ],
                ["The hour charge is a ceiling only after a replacement path exists. This rule does not repeat that dollar amount."],
            )
        ]


class UnassociatedAddress(CostRule):
    rule_id = "EC2-004"
    name = "UNASSOCIATED_ADDRESS"
    service = "EC2"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        if resource.get("resource_type") != "elastic_ip" or resource.get("state") != "unassociated":
            return []
        return [
            _recommendation(
                self,
                resource,
                "Review the unassociated Elastic IP",
                "This address appears unused based on the available evidence. Confirm it is not reserved for failover before release. No hourly price was loaded, so no saving is estimated.",
                "LOW",
                "RELEASE",
                [f"Public IP {(resource.get('metadata') or {}).get('public_ip') or 'unknown'}", "No association is recorded"],
                ["Release it only after DNS no longer points at it."],
            )
        ]


class TaggingGap(CostRule):
    rule_id = "TAG-001"
    name = "TAGGING_GAP"
    service = "Governance"

    def evaluate(self, resource: dict, today: date) -> list[dict]:
        return []


def tagging_gap(resources: list[dict]) -> dict | None:
    if not resources:
        return None
    tracked = ("Environment", "Owner", "CostCenter")
    missing = []
    for key in tracked:
        covered = 0
        for resource in resources:
            tags = resource.get("tags") or {}
            if any(tags.get(candidate) for candidate in (key, key.lower())):
                covered += 1
        percent = round(covered / len(resources) * 100)
        if percent < 80:
            missing.append(f"{key}: {percent}%")
    if not missing:
        return None
    rule = TaggingGap()
    return _recommendation(
        rule,
        {"resource_id": None, "service": "Governance", "metadata": {}, "metrics": {}},
        "Improve cost allocation tags",
        "Tag coverage is below 80% for one or more recommended keys. This is a governance improvement, not a direct saving.",
        "LOW",
        "GOVERNANCE",
        missing,
        ["Coverage counts resources stored for this account. Untagged resources hide environment in later reviews."],
        confidence="HIGH",
        data_quality="MEASURED",
    )


def _rank(rows: list[dict]) -> list[dict]:
    def score(row: dict) -> int:
        savings = int(as_decimal(row["estimated_monthly_savings"]))
        savings_score = min(40, savings)
        confidence_score = {"HIGH": 30, "MEDIUM": 20, "LOW": 10}.get(row["confidence"], 10)
        safety_score = {"LOW": 30, "MEDIUM": 15, "HIGH": 0}.get(row["risk_level"], 0)
        complexity_score = {"ARCHITECTURE": 20, "REVIEW": 10, "SCHEDULE": 5, "CLEANUP": 5, "RELEASE": 5, "GOVERNANCE": 5}.get(row["action_type"], 10)
        return savings_score + confidence_score + safety_score - complexity_score

    ordered = sorted(rows, key=score, reverse=True)
    for index, row in enumerate(ordered, start=1):
        row["priority"] = index
        row["priority_score"] = score(row)
    return ordered
