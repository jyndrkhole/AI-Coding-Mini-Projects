from datetime import date
from pathlib import Path

from app.services.mock_loader import load_json
from app.services.rules.engine import RuleRegistry

TODAY = date(2026, 10, 5)
ROOT = Path(__file__).resolve().parents[3]


def _resources() -> list[dict]:
    rows = []
    for name in ("ec2.json", "ebs.json", "rds.json", "s3.json", "lambda.json", "nat.json"):
        payload = load_json("resources", name)
        rows.extend(payload["resources"])
    metrics = {}
    for item in load_json("metrics", "metrics.json")["metrics"]:
        metrics.setdefault(item["resource_id"], {})[item["metric_name"]] = item
    for row in rows:
        row["metrics"] = metrics.get(row["resource_id"], {})
        row["metadata"] = row.get("metadata") or {}
        row["tags"] = row.get("tags") or {}
    return rows


def test_rules_do_not_invent_savings_or_resize_from_cpu_alone() -> None:
    findings = {item["rule_id"]: item for item in RuleRegistry().evaluate(_resources(), TODAY)}
    dev = findings["EC2-002"]
    assert dev["resource_id"] == "i-0devsched001"
    assert dev["estimated_monthly_savings"] == 0
    assert "business-hours" in dev["evidence"]["assumptions"][0]
    cpu = findings["EC2-001"]
    assert "Additional validation required" in cpu["description"]
    assert cpu["estimated_monthly_savings"] == 0
    volume = findings["EBS-001"]
    assert volume["resource_id"] == "vol-0unattached01"
    assert volume["estimated_monthly_savings"] == 0
    assert "delete" not in findings["EBS-003"]["description"].lower() or "do not delete" in findings["EBS-003"]["description"].lower()
    assert findings["NAT-001"]["title"] == "Architecture review required"
    assert findings["NAT-001"]["estimated_monthly_savings"] == 0
    assert "TAG-001" in findings
    text = " ".join(item["description"] for item in findings.values()).lower()
    assert "guaranteed saving" not in text


def test_idle_load_balancer_and_database_are_safe_cleanup_without_a_stored_price() -> None:
    findings = {
        item["resource_id"]: item
        for item in RuleRegistry().evaluate(
            [
                {
                    "resource_id": "arn:aws:elasticloadbalancing:us-east-1:1:loadbalancer/app/old/abc",
                    "resource_type": "load_balancer",
                    "service": "ELB",
                    "name": "old",
                    "metrics": {"RequestCount": {"average": 0, "sample_count": 14}},
                    "metadata": {},
                },
                {
                    "resource_id": "busy",
                    "resource_type": "load_balancer",
                    "service": "ELB",
                    "name": "busy",
                    "metrics": {"RequestCount": {"average": 12, "sample_count": 14}},
                    "metadata": {},
                },
                {
                    "resource_id": "db-idle",
                    "service": "RDS",
                    "instance_type": "db.t4g.medium",
                    "metrics": {
                        "CPUUtilization": {"average": 1.2, "sample_count": 14},
                        "DatabaseConnections": {"average": 0, "sample_count": 14},
                    },
                    "metadata": {},
                },
                {
                    "resource_id": "db-low-cpu",
                    "service": "RDS",
                    "instance_type": "db.t3.medium",
                    "metrics": {"CPUUtilization": {"average": 4, "sample_count": 14}},
                    "metadata": {},
                },
            ],
            TODAY,
        )
    }
    balancer = findings["arn:aws:elasticloadbalancing:us-east-1:1:loadbalancer/app/old/abc"]
    assert balancer["rule_id"] == "ELB-001"
    assert balancer["title"] == "Idle load balancer"
    assert balancer["action_type"] == "CLEANUP"
    assert balancer["risk_level"] == "LOW"
    assert balancer["estimated_monthly_savings"] == 0
    assert "busy" not in findings
    idle_db = findings["db-idle"]
    assert idle_db["title"] == "Idle database instance"
    assert idle_db["action_type"] == "CLEANUP"
    assert idle_db["estimated_monthly_savings"] == 0
    assert findings["db-low-cpu"]["action_type"] == "REVIEW"
