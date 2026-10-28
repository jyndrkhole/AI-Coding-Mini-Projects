"""What-if NPS arithmetic on copies of the scores. The stored survey is not modified."""

from __future__ import annotations

from dataclasses import replace

from app.analytics.nps import calculate_nps, classify_score
from app.data.normalizer import NormalizedResponse


def simulate_fix(
    responses: list[NormalizedResponse],
    theme_by_id: dict[str, str],
    theme: str,
    scenario: str,
    proportion: float = 1.0,
    score_delta: int = 2,
    response_ids: list[str] | None = None,
) -> dict:
    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    if not 0 <= proportion <= 1:
        raise ValueError("proportion must be between 0 and 1")
    selected = []
    for row in responses:
        if theme_by_id.get(row.response_id) != theme:
            continue
        if response_ids is not None and row.response_id not in set(response_ids):
            continue
        selected.append(row)
    detractors = [row for row in selected if classify_score(row.score) == "detractor"]
    detractors = sorted(detractors, key=lambda row: row.response_id)
    if scenario == "C":
        count = int(round(len(detractors) * proportion))
        targeted = detractors[:count]
    else:
        targeted = detractors
    changes: dict[str, int] = {}
    for row in targeted:
        if scenario == "A":
            changes[row.response_id] = 7
        elif scenario == "B":
            changes[row.response_id] = 10
        else:
            changes[row.response_id] = max(0, min(10, row.score + score_delta))
    simulated = [replace(row, score=changes[row.response_id]) if row.response_id in changes else row for row in responses]
    current = calculate_nps(responses)
    after = calculate_nps(simulated)
    delta = None if current["nps"] is None or after["nps"] is None else after["nps"] - current["nps"]
    descriptions = {
        "A": "Selected detractors in this theme are modelled as passives (score 7).",
        "B": "Selected detractors in this theme are modelled as promoters (score 10).",
        "C": f"A proportion of {proportion:.0%} of selected detractors is modelled as improving by {score_delta} points, capped at 10.",
    }
    return {
        "theme": theme,
        "scenario": scenario,
        "current_nps": current["nps"],
        "simulated_nps": after["nps"],
        "delta": delta,
        "affected_response_count": len(changes),
        "affected_response_ids": sorted(changes),
        "current_distribution": {
            "promoters": current["promoters"],
            "passives": current["passives"],
            "detractors": current["detractors"],
        },
        "simulated_distribution": {
            "promoters": after["promoters"],
            "passives": after["passives"],
            "detractors": after["detractors"],
        },
        "assumptions": [descriptions[scenario], "Responses outside the selected detractors keep their original scores."],
        "caveats": [
            "This is a hypothetical simulation, not a forecast.",
            "Resolving a complaint does not guarantee that the customer will change the score.",
            "Original survey scores are unchanged.",
        ],
    }
