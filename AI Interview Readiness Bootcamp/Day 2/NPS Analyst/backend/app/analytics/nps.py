"""Deterministic NPS. Percentages use a 0–100 scale. NPS is promoters minus detractors on that scale."""

from __future__ import annotations

from collections import defaultdict

from app.data.normalizer import NormalizedResponse


def classify_score(score: int) -> str:
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def calculate_nps(responses: list[NormalizedResponse]) -> dict:
    """NPS = promoter percentage − detractor percentage, using every valid response as the denominator."""
    total = len(responses)
    promoters = sum(1 for row in responses if classify_score(row.score) == "promoter")
    passives = sum(1 for row in responses if classify_score(row.score) == "passive")
    detractors = sum(1 for row in responses if classify_score(row.score) == "detractor")
    if total == 0:
        return {
            "total_responses": 0,
            "promoters": 0,
            "passives": 0,
            "detractors": 0,
            "promoter_percentage": None,
            "passive_percentage": None,
            "detractor_percentage": None,
            "nps": None,
        }
    promoter_percentage = promoters / total * 100
    passive_percentage = passives / total * 100
    detractor_percentage = detractors / total * 100
    return {
        "total_responses": total,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "promoter_percentage": promoter_percentage,
        "passive_percentage": passive_percentage,
        "detractor_percentage": detractor_percentage,
        "nps": promoter_percentage - detractor_percentage,
    }


def nps_by_month(responses: list[NormalizedResponse]) -> list[dict]:
    """Group by the month derived from the response date. Missing months are not invented."""
    grouped: dict[str, list[NormalizedResponse]] = defaultdict(list)
    for row in responses:
        grouped[row.analysis_month].append(row)
    results = []
    for month in sorted(grouped):
        summary = calculate_nps(grouped[month])
        summary["month"] = month
        results.append(summary)
    return results
