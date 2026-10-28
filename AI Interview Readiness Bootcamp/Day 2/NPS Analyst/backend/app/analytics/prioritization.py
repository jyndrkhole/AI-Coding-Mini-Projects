"""Separate rankings for customer impact, expected revenue at risk, and callbacks.

Customer-impact score = detractor count × theme severity / implementation complexity.
Expected revenue at risk is the sum from the revenue model and is not mixed into that score.
A theme with fewer responses than the minimum sample is listed apart from the definitive ranking.
"""

from __future__ import annotations

from app.core.config import LOW_SAMPLE_LABEL, THEME_OWNERS, Settings


def _impact(theme: dict, settings: Settings) -> float:
    severity = settings.theme_severity.get(theme["theme"], 1)
    complexity = settings.theme_complexity.get(theme["theme"], 1) or 1
    return theme["detractors"] * severity / complexity


def rank_themes(themes: list[dict], revenue_by_theme: list[dict], settings: Settings) -> dict:
    revenue_lookup = {row["label"]: row for row in revenue_by_theme}
    customer_rows = []
    revenue_rows = []
    held_back = []
    for theme in themes:
        if theme["theme"] == "UNCLEAR":
            continue
        revenue = revenue_lookup.get(theme["theme"], {})
        record = {
            "theme": theme["theme"],
            "comments": theme["comments"],
            "detractors": theme["detractors"],
            "nps": theme["nps"],
            "detractor_change": theme["detractor_change"],
            "customer_impact_score": _impact(theme, settings),
            "expected_revenue_at_risk_inr": revenue.get("estimated_expected_revenue_at_risk_inr"),
            "revenue_exposed_inr": revenue.get("revenue_exposed_inr"),
            "low_sample": theme["comments"] < settings.min_sample,
            "caution": LOW_SAMPLE_LABEL if theme["comments"] < settings.min_sample else None,
            "owner": THEME_OWNERS.get(theme["theme"], "Customer experience"),
            "formula": "customer_impact_score = detractors × severity / complexity",
        }
        if record["low_sample"]:
            held_back.append(record)
        else:
            customer_rows.append(record)
        revenue_rows.append(record)
    customer_rows.sort(key=lambda row: (-row["customer_impact_score"], row["theme"]))
    revenue_ranked = sorted(
        [row for row in revenue_rows if row["expected_revenue_at_risk_inr"] is not None],
        key=lambda row: (-row["expected_revenue_at_risk_inr"], row["theme"]),
    )
    volume = sorted(themes, key=lambda row: (-row["comments"], row["theme"]))
    volume_leader = next((row["theme"] for row in volume if row["theme"] != "UNCLEAR"), None)
    revenue_leader = revenue_ranked[0]["theme"] if revenue_ranked else None
    return {
        "customer_impact": customer_rows,
        "low_sample_themes": held_back,
        "revenue_at_risk": revenue_ranked,
        "highest_volume_theme": volume_leader,
        "highest_expected_revenue_theme": revenue_leader,
        "same_theme": volume_leader is not None and volume_leader == revenue_leader,
        "note": "Complaint volume and expected revenue at risk are separate rankings. A frequent complaint and a high-value complaint can justify different work.",
    }


def association_statement(themes: list[dict], period_nps_change: float | None) -> dict:
    candidates = [theme for theme in themes if theme["theme"] != "UNCLEAR" and theme.get("detractor_change") is not None]
    if not candidates or period_nps_change is None:
        return {
            "theme": None,
            "statement": "There is not enough monthly theme evidence to describe an association.",
        }
    leader = max(candidates, key=lambda theme: (theme["detractor_change"], -theme["comments"], theme["theme"]))
    if period_nps_change < 0 and leader["detractor_change"] > 0:
        statement = (
            f"{leader['theme']} complaints were associated with the decline. "
            "The association is a rise in detractor comments for that theme while overall NPS fell. "
            "It is not proof that the theme caused the change."
        )
    else:
        statement = (
            "No theme combined a rise in detractor comments with the overall NPS change in a way that supports a stronger claim. "
            "Theme frequency alone is not treated as a cause."
        )
    return {"theme": leader["theme"], "detractor_change": leader["detractor_change"], "statement": statement}
