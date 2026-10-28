"""Survey and analysis tables. Comment text lives on the response row, not on every derived record."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SurveyDataset(Base):
    __tablename__ = "survey_datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    row_count: Mapped[int] = mapped_column(Integer)
    valid_count: Mapped[int] = mapped_column(Integer)
    reporting_period_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reporting_period_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = (UniqueConstraint("dataset_id", "response_id", name="uq_dataset_response"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("survey_datasets.id"), index=True)
    response_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[str] = mapped_column(String(32))
    month: Mapped[str] = mapped_column(String(16))
    product: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tenure: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    annual_revenue_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_record_json: Mapped[str] = mapped_column(Text)


class CommentClassification(Base):
    __tablename__ = "comment_classifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    response_row_id: Mapped[int] = mapped_column(ForeignKey("survey_responses.id"), index=True)
    response_id: Mapped[str] = mapped_column(String(64), index=True)
    primary_theme: Mapped[str] = mapped_column(String(64))
    secondary_theme: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    classification_source: Mapped[str] = mapped_column(String(32))
    evidence_phrase: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("survey_datasets.id"), index=True)
    status: Mapped[str] = mapped_column(String(64))
    config_fingerprint: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(64))
    phase: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[int] = mapped_column(Integer)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column(Integer)
    evidence_json: Mapped[str] = mapped_column(Text)
    assumptions_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")


class CallbackCandidate(Base):
    __tablename__ = "callback_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    response_id: Mapped[str] = mapped_column(String(64), index=True)
    priority: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    suggested_action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_run_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_runs.id"), nullable=True, index=True)
    scenario_type: Mapped[str] = mapped_column(String(8))
    parameters_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LeadershipReport(Base):
    __tablename__ = "leadership_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), unique=True, index=True)
    alert_level: Mapped[str] = mapped_column(String(16))
    report_json: Mapped[str] = mapped_column(Text)
    fact_check_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ThemeAggregate(Base):
    __tablename__ = "theme_aggregates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    theme: Mapped[str] = mapped_column(String(64))
    comments: Mapped[int] = mapped_column(Integer)
    promoters: Mapped[int] = mapped_column(Integer)
    passives: Mapped[int] = mapped_column(Integer)
    detractors: Mapped[int] = mapped_column(Integer)
    nps: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_revenue_inr: Mapped[float | None] = mapped_column(Float, nullable=True)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    __table_args__ = (Index("ix_quality_dataset_type", "dataset_id", "issue_type"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("survey_datasets.id"), index=True)
    response_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    evidence_json: Mapped[str] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
