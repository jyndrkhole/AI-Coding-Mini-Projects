"""Cost scan. Later collectors are recorded as skipped instead of being invented."""

from datetime import datetime, timezone

from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.aws.cost_explorer import CostExplorerReader
from app.aws.credentials import build_aws_clients
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Account
from app.db.seed import seed_mock_data
from app.services.cost_store import replace_cost_records

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

    steps.extend(_skipped())
    return {"status": status, "steps": steps}
