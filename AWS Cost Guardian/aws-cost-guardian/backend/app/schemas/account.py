from datetime import datetime

from pydantic import BaseModel


class AccountResponse(BaseModel):
    aws_account_id: str
    account_alias: str | None
    region: str
    authenticated_role: str | None
    last_scan_at: datetime | None
    mock_aws: bool
    mode: str
