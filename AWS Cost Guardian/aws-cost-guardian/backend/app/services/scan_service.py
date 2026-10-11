"""Cost scan. Later collectors are recorded as skipped instead of being invented."""

from datetime import datetime, timezone

from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.aws.cost_explorer import CostExplorerReader
from app.aws.credentials import build_aws_clients, build_read_clients
from app.aws.inventory import collect_inventory
from app.aws.metrics_reader import collect_metrics
from app.aws.optimizer import collect_aws_recommendations
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Account
from app.db.seed import seed_mock_data
from app.services.cost_findings import findings_from_stored_costs
from app.services.cost_store import replace_cost_records
from app.services.resource_service import replace_generated_recommendations, replace_inventory, resource_views
from app.services.rules.engine import RuleRegistry

logger = get_logger(__name__)

SKIPPED_STEPS = (
    ("resources", "Resource inventory is not part of this cost scan."),
    ("metrics", "CloudWatch metrics are not part of this cost scan."),
    ("recommendations", "Recommendation collection is not part of this cost scan."),
)


def _step(service: str, status: str, error: str | None = None, detail: str | None = None) -> dict:
    return {
        "service": service,
        "status": status,
        "error": error,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _skipped() -> list[dict]:
    return [_step(service, "skipped", detail=detail) for service, detail in SKIPPED_STEPS]


def run_scan(session: Session, *, sts_client=None, ce_client=None, today=None) -> dict:
    settings = get_settings()
    today = today or datetime.now(timezone.utc).date()
    steps: list[dict] = []
    status = "completed"

    def add(step: dict) -> None:
        nonlocal status
        if step["status"] == "error":
            status = "completed_with_errors"
        steps.append(step)

    if settings.mock_aws:
        add(_step("sts", "skipped", detail="Demo mode does not call AWS."))
        try:
            seed_mock_data()
            account = session.query(Account).one()
            account.last_scan_at = datetime.now(timezone.utc)
            session.commit()
            add(_step("cost_explorer", "ok", detail="Loaded the demo cost dataset. No AWS calls were made."))
        except Exception:
            session.rollback()
            logger.exception("Demo cost load failed")
            add(_step("cost_explorer", "error", error="Cost data unavailable."))
        steps.extend(_skipped())
        return {"status": status, "steps": steps}

    if sts_client is None or ce_client is None:
        try:
            sts_client, ce_client = build_aws_clients()
        except Exception:
            logger.exception("AWS client setup failed")
            message = "AWS role assumption failed." if settings.aws_role_arn else "AWS credentials unavailable."
            add(_step("sts", "error", error=message))
            add(_step("cost_explorer", "skipped", detail="Cost Explorer was not called because credentials were not validated."))
            steps.extend(_skipped())
            return {"status": status, "steps": steps}

    try:
        identity = sts_client.get_caller_identity()
        account_id = str(identity["Account"])
        caller_arn = str(identity["Arn"])
    except Exception:
        logger.exception("Caller identity failed")
        message = "AWS role assumption failed." if settings.aws_role_arn else "AWS credentials unavailable."
        add(_step("sts", "error", error=message))
        add(_step("cost_explorer", "skipped", detail="Cost Explorer was not called because credentials were not validated."))
        steps.extend(_skipped())
        return {"status": status, "steps": steps}

    add(_step("sts", "ok", detail=f"Account {account_id}"))
    try:
        lines = CostExplorerReader(ce_client).collect(today)
        account = session.query(Account).filter_by(aws_account_id=account_id).one_or_none()
        if account is None:
            account = Account(
                aws_account_id=account_id,
                account_alias=None,
                region=settings.aws_region,
                role_arn=settings.aws_role_arn or caller_arn,
            )
            session.add(account)
            session.flush()
        else:
            account.region = settings.aws_region
            account.role_arn = settings.aws_role_arn or caller_arn
        replace_cost_records(session, account.id, lines)
        account.last_scan_at = datetime.now(timezone.utc)
        session.commit()
        add(_step("cost_explorer", "ok", detail=f"Stored {len(lines)} cost rows from Cost Explorer."))
    except ClientError as exc:
        session.rollback()
        logger.exception("Cost Explorer collection failed")
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"AccessDeniedException", "AccessDenied"}:
            message = "Missing IAM permission. Cost Explorer requires ce:GetCostAndUsage."
        else:
            message = "Cost Explorer unavailable."
        add(_step("cost_explorer", "error", error=message))
    except Exception:
        session.rollback()
        logger.exception("Cost Explorer collection failed")
        add(_step("cost_explorer", "error", error="Cost Explorer unavailable."))

    _collect_evidence(session, account_id, add)
    return {"status": status, "steps": steps}


def _collect_evidence(session: Session, account_id: str, add) -> None:
    account = session.query(Account).filter_by(aws_account_id=account_id).one_or_none()
    if account is None:
        add(_step("resources", "skipped", detail="Inventory was not stored because the account row was not saved."))
        add(_step("metrics", "skipped", detail="Metrics were not collected."))
        add(_step("recommendations", "skipped", detail="Rules were not run."))
        return
    try:
        clients = build_read_clients()
    except Exception:
        logger.exception("Read-only AWS clients were not created")
        add(_step("resources", "error", error="AWS credentials unavailable."))
        add(_step("metrics", "skipped", detail="Metrics were not collected."))
        add(_step("recommendations", "skipped", detail="AWS recommendations were not collected."))
        return
    resources, inventory_problems = collect_inventory(clients)
    metrics, metric_problem = collect_metrics(clients.get("cloudwatch"), resources)
    aws_rows, aws_problems = collect_aws_recommendations(clients)
    try:
        replace_inventory(session, account.id, resources, metrics)
        views = resource_views(session, account.id)
        rule_rows = RuleRegistry().evaluate(views)
        generated = rule_rows + aws_rows
        for index, row in enumerate(generated, start=1):
            row["priority"] = index
        finding_rows = [_finding_row(item) for item in findings_from_stored_costs(session, account.id)]
        for offset, row in enumerate(finding_rows, start=len(generated) + 1):
            row["priority"] = offset
        replace_generated_recommendations(session, account.id, generated + finding_rows)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Inventory persistence failed")
        add(_step("resources", "error", error="Inventory could not be stored."))
        return
    add(_step("resources", "ok", detail=f"Stored {len(resources)} resources."))
    add(_step("metrics", "ok" if metric_problem is None else "error", error=None if metric_problem is None else metric_problem["error"], detail=f"Stored {len(metrics)} metric summaries."))
    if inventory_problems:
        add(_step("resources", "error", error="; ".join(problem["error"] for problem in inventory_problems)))
    if aws_problems:
        add(_step("aws_recommendations", "error", error="; ".join(problem["error"] for problem in aws_problems)))
    else:
        add(_step("aws_recommendations", "ok", detail=f"Stored {len(aws_rows)} AWS recommendations."))
    add(_step("rules", "ok", detail=f"Stored {len(rule_rows)} internal rule recommendations."))


def _finding_row(item: dict) -> dict:
    monthly = item["estimated_monthly_savings"]
    return {
        "resource_id": item["resource_id"],
        "rule_id": "COST-EXPLORER",
        "source": "COST_EXPLORER",
        "service": item["service"],
        "title": item["title"],
        "description": item["description"],
        "evidence": {
            "summary": item["evidence_summary"],
            "assumptions": item["assumptions"],
            "client_brief": item.get("client_brief") or "",
            "client_ask": item.get("client_ask") or "",
            "next_steps": item.get("next_steps") or [],
        },
        "current_monthly_cost": item["current_monthly_cost"],
        "estimated_monthly_savings": monthly,
        "estimated_annual_savings": item["estimated_annual_savings"],
        "confidence": item["confidence"],
        "data_quality": item["data_quality"],
        "risk_level": item["risk_level"],
        "priority": item["priority"],
        "action_type": item["action_type"],
        "status": "OPEN",
    }
