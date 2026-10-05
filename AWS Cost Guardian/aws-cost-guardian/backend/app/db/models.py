"""Persistence models for collected FinOps evidence."""

from datetime import date as date_type
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    aws_account_id: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    account_alias: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(64))
    role_arn: Mapped[str | None] = mapped_column(String(512))
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CostRecord(Base):
    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)
    service: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(64))
    usage_type: Mapped[str] = mapped_column(String(128), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(32), index=True)


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("account_id", "resource_id", name="uq_account_resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    resource_id: Mapped[str] = mapped_column(String(512), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    service: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str | None] = mapped_column(String(64))
    instance_type: Mapped[str | None] = mapped_column(String(64))
    environment: Mapped[str | None] = mapped_column(String(64))
    tags_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(128))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period: Mapped[int] = mapped_column()
    average: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    minimum: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    maximum: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    sample_count: Mapped[int | None] = mapped_column()


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(512))
    rule_id: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(64))
    service: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    current_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estimated_monthly_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estimated_annual_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    confidence: Mapped[str] = mapped_column(String(32))
    data_quality: Mapped[str] = mapped_column(String(32))
    risk_level: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column()
    action_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    scenario_type: Mapped[str] = mapped_column(String(64))
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    current_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    projected_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    potential_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    assumptions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    report_month: Mapped[str] = mapped_column(String(7))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    previous_month_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    potential_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    realized_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
