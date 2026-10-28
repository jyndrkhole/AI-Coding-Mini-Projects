"""Assemble the deterministic analysis the tools and the API share."""

from __future__ import annotations

from app.analytics.confidence import build_confidence
from app.analytics.data_quality import build_quality
from app.analytics.nps import calculate_nps
from app.analytics.prioritization import association_statement, rank_themes
from app.analytics.revenue_risk import build_revenue
from app.analytics.themes import aggregate_themes, classify_responses
from app.analytics.trends import alert_for, period_change, verify_reference_claims
from app.core.config import Settings, get_settings
from app.data.normalizer import NormalizedResponse
from app.services.callback_service import build_callbacks


def build_bundle(
    responses: list[NormalizedResponse],
    validation_issues: list | None = None,
    settings: Settings | None = None,
    metadata: dict | None = None,
) -> dict:
    settings = settings or get_settings()
    validation_issues = validation_issues or []
    classified = classify_responses(responses)
    month_axis = sorted({row.analysis_month for row in responses})
    themes = aggregate_themes(classified, month_axis)
    quality = build_quality(responses, classified, validation_issues)
    revenue = build_revenue(classified, settings)
    confidence = build_confidence(responses, settings)
    months = confidence["months"]
    period = period_change(months)
    return {
        "metadata": metadata or {},
        "settings": settings,
        "overview": calculate_nps(responses),
        "months": months,
        "period": period,
        "alert": alert_for(months, settings),
        "reference_claims": verify_reference_claims(months),
        "segments": confidence["segments"],
        "confidence": confidence,
        "themes": themes,
        "classified": classified,
        "responses": responses,
        "quality": quality,
        "revenue": revenue,
        "priorities": rank_themes(themes, revenue["by_theme"], settings),
        "association": association_statement(themes, period["period_nps_change"]),
        "callbacks": build_callbacks(classified, quality, settings),
    }
