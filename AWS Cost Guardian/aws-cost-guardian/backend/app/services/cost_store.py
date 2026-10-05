"""Stored cost rows. Writers replace a full collection; readers sum those rows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import CostRecord


@dataclass(frozen=True)
class CostLine:
    date: date
    service: str
    region: str
    usage_type: str
    amount: Decimal
    currency: str
    source: str


def replace_cost_records(session: Session, account_id: int, lines: list[CostLine]) -> int:
    session.query(CostRecord).filter(CostRecord.account_id == account_id).delete()
    for line in lines:
        session.add(
            CostRecord(
                account_id=account_id,
                date=line.date,
                service=line.service,
                region=line.region,
                usage_type=line.usage_type,
                amount=line.amount,
                currency=line.currency,
                source=line.source,
            )
        )
    return len(lines)
