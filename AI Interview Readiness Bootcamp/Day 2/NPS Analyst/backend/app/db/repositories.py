"""Load and store survey rows. Derived comment text is not copied into every table."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    AnalysisRun,
    CallbackCandidate,
    CommentClassification,
    DataQualityIssue,
    LeadershipReport,
    Recommendation,
    SimulationRun,
    SurveyDataset,
    SurveyResponse,
    ThemeAggregate,
)
from app.data.normalizer import NormalizedResponse

VALIDATION_TYPES = {
    "EMPTY_COMMENT",
    "MISSING_REVENUE",
    "INVALID_SCORE",
    "DUPLICATE_RESPONSE_ID",
    "MONTH_DATE_MISMATCH",
    "MISSING_RESPONSE_ID",
    "INVALID_DATE",
    "NEGATIVE_REVENUE",
    "INVALID_REVENUE",
    "MISSING_SEGMENT",
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def dataset_by_checksum(session: Session, checksum: str) -> SurveyDataset | None:
    return session.scalar(select(SurveyDataset).where(SurveyDataset.checksum == checksum))


def dataset_by_id(session: Session, dataset_id: str) -> SurveyDataset | None:
    return session.get(SurveyDataset, dataset_id)


def list_datasets(session: Session) -> list[SurveyDataset]:
    return list(session.scalars(select(SurveyDataset).order_by(SurveyDataset.uploaded_at.desc())))


def save_dataset(session: Session, dataset: SurveyDataset, responses: list[SurveyResponse], issues: list[DataQualityIssue]) -> None:
    session.add(dataset)
    session.add_all(responses)
    session.add_all(issues)
    session.commit()


def responses_for(session: Session, dataset_id: str) -> list[NormalizedResponse]:
    rows = session.scalars(select(SurveyResponse).where(SurveyResponse.dataset_id == dataset_id).order_by(SurveyResponse.id)).all()
    normalized = []
    for row in rows:
        year_month = row.date[:7]
        normalized.append(
            NormalizedResponse(
                response_id=row.response_id,
                date=row.date,
                month=row.month,
                analysis_month=year_month,
                product=row.product,
                tenure=row.tenure,
                channel=row.channel,
                score=row.score,
                comment=row.comment,
                annual_revenue_inr=row.annual_revenue_inr,
            )
        )
    return normalized


def validation_issues(session: Session, dataset_id: str) -> list[dict]:
    rows = session.scalars(select(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset_id)).all()
    issues = []
    for row in rows:
        if row.issue_type not in VALIDATION_TYPES:
            continue
        issues.append(
            {
                "response_id": row.response_id,
                "issue_type": row.issue_type,
                "severity": row.severity,
                "evidence": json.loads(row.evidence_json),
                "recommended_review": True,
                "row_number": None,
            }
        )
    return issues


def latest_run(session: Session, dataset_id: str) -> AnalysisRun | None:
    return session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.dataset_id == dataset_id, AnalysisRun.status.in_(("completed", "completed_with_unavailable_sections")))
        .order_by(AnalysisRun.completed_at.desc())
    )


def run_by_id(session: Session, run_id: str) -> AnalysisRun | None:
    return session.get(AnalysisRun, run_id)


def save_run(session: Session, run: AnalysisRun, payload: dict) -> None:
    session.add(run)
    for row in payload["trace"]:
        session.add(
            AgentRun(
                analysis_run_id=run.id,
                agent_name=row["agent"],
                phase=row["phase"],
                status=row["status"],
                duration_ms=row["duration_ms"],
                output_json=None,
                error_json=json.dumps({"error": row["error"]}) if row.get("error") else None,
            )
        )
    report = payload["report"]
    for action in report.get("actions", []):
        session.add(
            Recommendation(
                analysis_run_id=run.id,
                title=action["title"],
                category=action["category"],
                priority=action["priority"],
                evidence_json=json.dumps({"evidence": action["evidence"]}),
                assumptions_json=json.dumps(report.get("caveats", {}).get("assumptions", {})),
                status="PROPOSED",
            )
        )
    for callback in report.get("callbacks", []):
        session.add(
            CallbackCandidate(
                analysis_run_id=run.id,
                response_id=callback["response_id"],
                priority=callback["priority_components"]["priority_score"],
                reason=callback["reason"],
                suggested_action=callback["suggested_action"],
                status="RECOMMENDED",
            )
        )
    for theme in payload.get("themes", []):
        session.add(
            ThemeAggregate(
                analysis_run_id=run.id,
                theme=theme["theme"],
                comments=theme["comments"],
                promoters=theme["promoters"],
                passives=theme["passives"],
                detractors=theme["detractors"],
                nps=theme["nps"],
                annual_revenue_inr=theme["annual_revenue_inr"],
            )
        )
    session.add(
        LeadershipReport(
            analysis_run_id=run.id,
            alert_level=report.get("alert_level", "AMBER"),
            report_json=json.dumps(report),
            fact_check_json=json.dumps(payload["fact_check"]),
            created_at=now(),
        )
    )
    session.commit()


def replace_classifications(session: Session, dataset_id: str, classified: list[dict]) -> None:
    response_rows = session.scalars(select(SurveyResponse).where(SurveyResponse.dataset_id == dataset_id)).all()
    ids = [row.id for row in response_rows]
    if ids:
        session.query(CommentClassification).filter(CommentClassification.response_row_id.in_(ids)).delete(synchronize_session=False)
    by_response = {row.response_id: row.id for row in response_rows}
    for item in classified:
        row_id = by_response.get(item["response_id"])
        if row_id is None:
            continue
        session.add(
            CommentClassification(
                response_row_id=row_id,
                response_id=item["response_id"],
                primary_theme=item["primary_theme"],
                secondary_theme=item["secondary_theme"],
                sentiment=item["sentiment"],
                confidence=item["confidence"],
                classification_source=item["classification_source"],
                evidence_phrase=item["evidence_phrase"],
            )
        )
    session.commit()


def save_simulation(session: Session, simulation: SimulationRun) -> None:
    session.add(simulation)
    session.commit()


def report_for_run(session: Session, run_id: str) -> LeadershipReport | None:
    return session.scalar(select(LeadershipReport).where(LeadershipReport.analysis_run_id == run_id))


def callbacks_for_run(session: Session, run_id: str) -> list[CallbackCandidate]:
    return list(session.scalars(select(CallbackCandidate).where(CallbackCandidate.analysis_run_id == run_id).order_by(CallbackCandidate.priority.desc())))


def trace_for_run(session: Session, run_id: str) -> list[AgentRun]:
    return list(session.scalars(select(AgentRun).where(AgentRun.analysis_run_id == run_id).order_by(AgentRun.id)))
