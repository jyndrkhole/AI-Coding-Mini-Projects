"""Data-quality findings. Original scores and comments are never rewritten."""

from __future__ import annotations

from collections import Counter

from app.analytics.themes import sentiment_of
from app.data.normalizer import NormalizedResponse


def issue_to_dict(issue) -> dict:
    if isinstance(issue, dict):
        return issue
    return {
        "response_id": issue.response_id,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "evidence": issue.evidence,
        "recommended_review": issue.recommended_review,
        "row_number": issue.row_number,
    }


def contradiction_issues(responses: list[NormalizedResponse]) -> list[dict]:
    """Flag praise with a low score, and a harsh comment with a promoter score. Do not change the score."""
    found = []
    for row in responses:
        sentiment = sentiment_of(row.comment)
        if sentiment == "POSITIVE" and row.score <= 6:
            found.append(_contradiction(row, sentiment))
        elif sentiment == "NEGATIVE" and row.score >= 9:
            found.append(_contradiction(row, sentiment))
    return found


def _contradiction(row: NormalizedResponse, sentiment: str) -> dict:
    return {
        "response_id": row.response_id,
        "issue_type": "POSSIBLE_SCORE_INTERPRETATION_ERROR",
        "severity": "MEDIUM",
        "evidence": {"score": row.score, "comment": row.comment, "sentiment": sentiment},
        "recommended_review": True,
        "row_number": None,
    }


def extreme_revenue_issues(responses: list[NormalizedResponse]) -> list[dict]:
    known = sorted(row.annual_revenue_inr for row in responses if row.annual_revenue_inr is not None)
    if len(known) < 5:
        return []
    median = known[len(known) // 2]
    if median <= 0:
        return []
    threshold = median * 10
    flagged = []
    for row in responses:
        if row.annual_revenue_inr is not None and row.annual_revenue_inr > threshold:
            flagged.append(
                {
                    "response_id": row.response_id,
                    "issue_type": "EXTREME_VALUE",
                    "severity": "MEDIUM",
                    "evidence": {"annual_revenue_inr": row.annual_revenue_inr, "threshold": threshold},
                    "recommended_review": True,
                    "row_number": None,
                }
            )
    return flagged


def low_confidence_issues(classified: list[dict]) -> list[dict]:
    issues = []
    for item in classified:
        if item["primary_theme"] == "UNCLEAR" and item["sentiment"] not in {"UNKNOWN", ""} and item["confidence"] < 0.5:
            issues.append(
                {
                    "response_id": item["response_id"],
                    "issue_type": "LOW_CONFIDENCE_CLASSIFICATION",
                    "severity": "LOW",
                    "evidence": {"comment": item.get("comment"), "sentiment": item["sentiment"]},
                    "recommended_review": True,
                    "row_number": None,
                }
            )
    return issues


def build_quality(responses: list[NormalizedResponse], classified: list[dict], validation_issues: list) -> dict:
    issues = [issue_to_dict(issue) for issue in validation_issues]
    issues.extend(contradiction_issues(responses))
    issues.extend(extreme_revenue_issues(responses))
    issues.extend(low_confidence_issues(classified))
    by_type = Counter(issue["issue_type"] for issue in issues)
    flags_by_response: dict[str, list[str]] = {}
    for issue in issues:
        if issue.get("response_id"):
            flags_by_response.setdefault(issue["response_id"], []).append(issue["issue_type"])
    return {
        "issues": issues,
        "by_type": dict(by_type),
        "total_issues": len(issues),
        "contradiction_count": by_type.get("POSSIBLE_SCORE_INTERPRETATION_ERROR", 0),
        "missing_comment_count": by_type.get("EMPTY_COMMENT", 0),
        "missing_revenue_count": by_type.get("MISSING_REVENUE", 0),
        "invalid_score_count": by_type.get("INVALID_SCORE", 0),
        "duplicate_count": by_type.get("DUPLICATE_RESPONSE_ID", 0),
        "flags_by_response": flags_by_response,
        "note": "Rows are flagged for review. Scores and comments are not rewritten.",
    }
