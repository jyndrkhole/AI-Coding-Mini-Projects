"""Read-only tools. Numbers come from the deterministic bundle, not from a model."""

from __future__ import annotations

from contextvars import ContextVar

from app.analytics.revenue_risk import high_value_detractors
from app.analytics.simulation import simulate_fix
from app.analytics.themes import examples_for

CTX: ContextVar["ToolContext"] = ContextVar("nps_tool_context")


class ToolContext:
    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.tool_calls: list[dict] = []


def _bundle() -> dict:
    return CTX.get().bundle


def _record(name: str, arguments: dict, payload: dict) -> dict:
    CTX.get().tool_calls.append({"tool": name, "arguments": arguments})
    return payload


def get_nps_overview() -> dict:
    overview = dict(_bundle()["overview"])
    overview["alert"] = _bundle()["alert"]
    return _record("get_nps_overview", {}, overview)


def get_nps_by_month() -> dict:
    bundle = _bundle()
    return _record(
        "get_nps_by_month",
        {},
        {"months": bundle["months"], "period": bundle["period"], "reference_claims": bundle["reference_claims"]},
    )


def get_nps_by_segment(segment_type: str) -> dict:
    segments = _bundle()["segments"]
    if segment_type not in segments:
        return _record(
            "get_nps_by_segment",
            {"segment_type": segment_type},
            {"error": "segment_type must be product, channel, or tenure", "segments": []},
        )
    return _record(
        "get_nps_by_segment",
        {"segment_type": segment_type},
        {"segment_type": segment_type, "segments": segments[segment_type]},
    )


def get_confidence_analysis(segment: str = "overall") -> dict:
    confidence = _bundle()["confidence"]
    if segment == "overall":
        payload = {"segment": "overall", "result": confidence["overall"], "note": confidence["ranking_note"]}
    elif segment in confidence["segments"]:
        payload = {
            "segment": segment,
            "results": confidence["segments"][segment],
            "minimum_sample": confidence["minimum_sample"],
            "note": confidence["ranking_note"],
        }
    else:
        payload = {"error": "segment must be overall, product, channel, or tenure"}
    return _record("get_confidence_analysis", {"segment": segment}, payload)


def get_comment_themes() -> dict:
    bundle = _bundle()
    return _record(
        "get_comment_themes",
        {},
        {"themes": bundle["themes"], "association": bundle["association"], "priorities": bundle["priorities"]},
    )


def get_theme_by_month(theme: str) -> dict:
    for record in _bundle()["themes"]:
        if record["theme"] == theme:
            return _record("get_theme_by_month", {"theme": theme}, {"theme": theme, "monthly": record["monthly"]})
    return _record("get_theme_by_month", {"theme": theme}, {"error": "Theme is not in the results.", "monthly": []})


def get_theme_by_segment(theme: str, segment_type: str) -> dict:
    if segment_type not in {"product", "channel", "tenure"}:
        return _record(
            "get_theme_by_segment",
            {"theme": theme, "segment_type": segment_type},
            {"error": "segment_type must be product, channel, or tenure"},
        )
    counts: dict[str, int] = {}
    for item in _bundle()["classified"]:
        if item["primary_theme"] != theme:
            continue
        label = item[segment_type] or "Unknown"
        counts[label] = counts.get(label, 0) + 1
    rows = [{"segment": label, "comments": counts[label]} for label in sorted(counts)]
    return _record("get_theme_by_segment", {"theme": theme, "segment_type": segment_type}, {"theme": theme, "rows": rows})


def get_comment_examples(theme: str, sentiment: str | None = None, limit: int = 3) -> dict:
    examples = examples_for(_bundle()["classified"], theme, sentiment, limit=limit)
    return _record(
        "get_comment_examples",
        {"theme": theme, "sentiment": sentiment, "limit": limit},
        {"theme": theme, "sentiment": sentiment, "examples": examples},
    )


def get_theme_sentiment_summary(theme: str | None = None) -> dict:
    rows = _bundle()["classified"]
    if theme:
        rows = [row for row in rows if row["primary_theme"] == theme]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["sentiment"]] = counts.get(row["sentiment"], 0) + 1
    return _record("get_theme_sentiment_summary", {"theme": theme}, {"theme": theme or "ALL", "sentiments": counts})


def get_revenue_at_risk() -> dict:
    revenue = dict(_bundle()["revenue"])
    revenue.pop("per_response", None)
    return _record("get_revenue_at_risk", {}, revenue)


def get_revenue_by_segment(segment_type: str) -> dict:
    revenue = _bundle()["revenue"]
    key = {"product": "by_product", "channel": "by_channel", "tenure": "by_tenure", "nps_group": "by_group", "month": "by_month", "theme": "by_theme"}.get(segment_type)
    if key is None:
        return _record("get_revenue_by_segment", {"segment_type": segment_type}, {"error": "Unknown segment_type.", "rows": []})
    return _record("get_revenue_by_segment", {"segment_type": segment_type}, {"segment_type": segment_type, "rows": revenue[key]})


def find_high_value_detractors(limit: int = 15) -> dict:
    rows = high_value_detractors(_bundle()["classified"], _bundle()["settings"], limit=limit)
    return _record("find_high_value_detractors", {"limit": limit}, {"customers": rows})


def find_score_comment_mismatches() -> dict:
    issues = [
        issue
        for issue in _bundle()["quality"]["issues"]
        if issue["issue_type"] == "POSSIBLE_SCORE_INTERPRETATION_ERROR"
    ]
    return _record("find_score_comment_mismatches", {}, {"count": len(issues), "issues": issues})


def get_data_quality_summary() -> dict:
    quality = _bundle()["quality"]
    return _record(
        "get_data_quality_summary",
        {},
        {
            "total_issues": quality["total_issues"],
            "by_type": quality["by_type"],
            "contradiction_count": quality["contradiction_count"],
            "missing_comment_count": quality["missing_comment_count"],
            "missing_revenue_count": quality["missing_revenue_count"],
            "invalid_score_count": quality["invalid_score_count"],
            "duplicate_count": quality["duplicate_count"],
            "note": quality["note"],
        },
    )


def get_prioritized_themes() -> dict:
    return _record("get_prioritized_themes", {}, _bundle()["priorities"])


def estimate_fix_impact(theme: str, scenario: str = "A") -> dict:
    bundle = _bundle()
    theme_by_id = {item["response_id"]: item["primary_theme"] for item in bundle["classified"]}
    try:
        result = simulate_fix(bundle["responses"], theme_by_id, theme, scenario)
    except ValueError as exc:
        result = {"error": str(exc)}
    return _record("estimate_fix_impact", {"theme": theme, "scenario": scenario}, result)


def get_callback_candidates(limit: int | None = None) -> dict:
    rows = _bundle()["callbacks"]
    if limit is not None:
        rows = rows[:limit]
    return _record("get_callback_candidates", {"limit": limit}, {"candidates": rows, "contact_policy": "Recommendations only. No customer is contacted by this system."})


def get_survey_metadata() -> dict:
    return _record("get_survey_metadata", {}, _bundle().get("metadata", {}))
