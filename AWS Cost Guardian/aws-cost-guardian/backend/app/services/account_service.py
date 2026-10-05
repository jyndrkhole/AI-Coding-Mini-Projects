"""Read the connected account. Phase 1 serves the seeded demo account."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import FinOpsError
from app.db.models import Account

AWS_CREDENTIALS_UNAVAILABLE = (
    "AWS credentials unavailable. Turn on demo mode with MOCK_AWS=true to explore the dashboard."
)
DEMO_ACCOUNT_ID = "123456789012"


def require_account(session: Session) -> Account:
    query = session.query(Account)
    if not get_settings().mock_aws:
        query = query.filter(Account.aws_account_id != DEMO_ACCOUNT_ID)
    account = query.order_by(Account.id.desc()).first()
    if account is None:
        if get_settings().mock_aws:
            raise FinOpsError("Cost data unavailable.", status_code=503)
        raise FinOpsError(AWS_CREDENTIALS_UNAVAILABLE, status_code=503)
    return account


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_account(session: Session) -> dict:
    settings = get_settings()
    account = require_account(session)
    return {
        "aws_account_id": account.aws_account_id,
        "account_alias": account.account_alias,
        "region": account.region,
        "authenticated_role": account.role_arn,
        "last_scan_at": _as_utc(account.last_scan_at),
        "mock_aws": settings.mock_aws,
        "mode": "demo" if settings.mock_aws else "aws",
    }
