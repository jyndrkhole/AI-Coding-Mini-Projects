"""Leadership brief. Every number in the claims list is copied from a tool result."""

from __future__ import annotations

from app.agents import tools
from app.agents.prompts import REPORT_WRITER

MONTH_LABELS = {"2026-07": "July 2026", "2026-08": "August 2026", "2026-09": "September 2026"}


def _month(value: str | None) -> str:
    if value is None:
        return "the period"
    return MONTH_LABELS.get(value, value)


def _nps(value) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.1f}"


def _inr(value) -> str:
    if value is None:
        return "unavailable"
    return f"₹{value:,.0f}"


def _claims() -> tuple[list[dict], list[str]]:
    claims = []
    overview = tools.get_nps_overview()
    for metric in ("nps", "promoters", "passives", "detractors", "total_responses"):
        claims.append({"metric": metric, "scope": "overall", "value": overview[metric]})
    monthly = tools.get_nps_by_month()
    for row in monthly["months"]:
        for metric in ("nps", "promoters", "passives", "detractors", "total_responses"):
            claims.append({"metric": metric, "scope": row["month"], "value": row[metric]})
    revenue = tools.get_revenue_at_risk()
    for metric in ("revenue_exposed_inr", "estimated_expected_revenue_at_risk_inr", "missing_revenue_count"):
        claims.append({"metric": metric, "scope": "overall", "value": revenue[metric]})
    named = []
    for segment_type in ("product", "channel", "tenure"):
        for row in tools.get_nps_by_segment(segment_type)["segments"]:
            claims.append({"metric": "nps", "scope": f"{segment_type}:{row['segment']}", "value": row["nps"]})
            claims.append({"metric": "total_responses", "scope": f"{segment_type}:{row['segment']}", "value": row["total_responses"]})
    for theme in tools.get_comment_themes()["themes"]:
        if theme["theme"] == "UNCLEAR":
            continue
        named.append(theme["theme"])
        claims.append({"metric": "nps", "scope": f"theme:{theme['theme']}", "value": theme["nps"]})
        claims.append({"metric": "detractors", "scope": f"theme:{theme['theme']}", "value": theme["detractors"]})
    return claims, named


def _unavailable(agent: str) -> dict:
    return {"status": "unavailable", "detail": f"{agent} did not complete. No replacement finding was added."}


async def run(score: dict, voice: dict, churn: dict, planner: dict, correction: list | None = None) -> dict:
    overview = tools.get_nps_overview()
    monthly = tools.get_nps_by_month()
    revenue = tools.get_revenue_at_risk()
    quality = tools.get_data_quality_summary()
    alert = overview["alert"]
    period = monthly["period"]
    claims, named_themes = _claims()
    quotes = voice.get("quotes", []) if voice.get("available") else []
    callbacks = planner.get("callbacks", []) if planner.get("available") else []
    low_samples = score.get("low_samples", []) if score.get("available") else []
    headline = (
        f"NPS moved from {_nps(period.get('first_nps'))} in {_month(period.get('first_month'))} "
        f"to {_nps(period.get('last_nps'))} in {_month(period.get('last_month'))}."
    )
    why = _unavailable("VoiceOfCustomerAgent")
    if voice.get("available"):
        why = {
            "status": "available",
            "association": voice["association"],
            "negative_themes": [
                {"theme": theme["theme"], "detractors": theme["detractors"], "nps": theme["nps"], "comments": theme["comments"]}
                for theme in voice["negative_themes"]
            ],
            "positive_themes": [
                {"theme": theme["theme"], "promoters": theme["promoters"], "nps": theme["nps"]}
                for theme in voice["positive_themes"]
            ],
        }
    financial = _unavailable("ChurnRiskAgent")
    if churn.get("available"):
        financial = {
            "status": "available",
            "revenue_exposed_inr": revenue["revenue_exposed_inr"],
            "estimated_expected_revenue_at_risk_inr": revenue["estimated_expected_revenue_at_risk_inr"],
            "assumptions": revenue["assumptions"],
            "missing_revenue_count": revenue["missing_revenue_count"],
            "coverage_percentage": revenue["coverage_percentage"],
            "highest_volume_theme": churn.get("volume_leader"),
            "highest_expected_revenue_theme": churn.get("revenue_leader"),
            "volume_and_revenue_same_theme": churn.get("volume_and_revenue_same_theme"),
            "statement": churn.get("statement"),
        }
    report = {
        "agent": "ReportWriterAgent",
        "available": True,
        "instructions": REPORT_WRITER.strip(),
        "alert_level": alert["level"],
        "alert_reasons": alert["reasons"],
        "headline": headline,
        "nps_performance": {
            "status": "available" if score.get("available") else "unavailable",
            "overall": {key: overview.get(key) for key in ("nps", "total_responses", "promoters", "passives", "detractors", "promoter_percentage", "passive_percentage", "detractor_percentage")},
            "months": [
                {
                    "month": row["month"],
                    "label": _month(row["month"]),
                    "nps": row["nps"],
                    "nps_change": row.get("nps_change"),
                    "total_responses": row["total_responses"],
                    "promoters": row["promoters"],
                    "passives": row["passives"],
                    "detractors": row["detractors"],
                    "caution": row.get("caution"),
                    "confidence_low": row.get("confidence_low"),
                    "confidence_high": row.get("confidence_high"),
                }
                for row in monthly["months"]
            ],
            "period_nps_change": period.get("period_nps_change"),
            "reference_claims": monthly["reference_claims"],
            "low_samples": low_samples,
        },
        "why_it_moved": why,
        "financial_exposure": financial,
        "actions": planner.get("actions", []) if planner.get("available") else [],
        "actions_status": "available" if planner.get("available") else "unavailable",
        "callbacks": [
            {
                "response_id": row["response_id"],
                "product": row["product"],
                "score": row["score"],
                "annual_revenue_inr": row["annual_revenue_inr"],
                "nps_classification": row["nps_classification"],
                "theme": row["theme"],
                "reason": row["reason"],
                "timeframe": row["timeframe"],
                "suggested_action": row["suggested_action"],
                "recommended_owner": row["recommended_owner"],
                "priority_components": row["priority_components"],
            }
            for row in callbacks
        ],
        "caveats": {
            "contradiction_count": quality["contradiction_count"],
            "missing_comment_count": quality["missing_comment_count"],
            "missing_revenue_count": quality["missing_revenue_count"],
            "low_samples": low_samples,
            "assumptions": revenue["assumptions"],
            "notes": [
                "Scores that conflict with comments were flagged and left unchanged.",
                "Churn probabilities are assumptions, not measured attrition.",
                "Expected revenue at risk is not actual lost revenue.",
                "Future with Shivank Bank and this survey are fictional. This is not a production banking system.",
                "Callback rows are recommendations. The application does not contact customers or change bank records.",
            ],
        },
        "claims": claims,
        "named_themes": named_themes,
        "quotes": [{"response_id": quote["response_id"], "comment": quote["comment"], "theme": quote.get("theme"), "score": quote.get("score")} for quote in quotes],
        "callback_ids": [row["response_id"] for row in callbacks],
        "assumptions_disclosed": True,
        "small_samples_disclosed": True,
        "missing_data_disclosed": True,
        "missing_revenue_treated_as_zero": False,
        "correction_applied": bool(correction),
        "tools_used": ["get_nps_overview", "get_nps_by_month", "get_nps_by_segment", "get_revenue_at_risk", "get_data_quality_summary", "get_comment_themes"],
    }
    return report
