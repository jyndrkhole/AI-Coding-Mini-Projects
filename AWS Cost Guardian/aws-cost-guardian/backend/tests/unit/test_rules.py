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
