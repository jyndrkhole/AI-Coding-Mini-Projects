"""Callback recommendations. The application never contacts a customer."""

from __future__ import annotations

from app.core.config import THEME_OWNERS, Settings

SEVERE_THEMES = {"OTP_AND_LOGIN", "ACCOUNT_ACCESS", "FEES_AND_CHARGES", "CUSTOMER_SUPPORT"}


def build_callbacks(classified: list[dict], quality: dict, settings: Settings) -> list[dict]:
    flags = quality.get("flags_by_response", {})
    detractor_revenue = sorted(
        item["annual_revenue_inr"]
        for item in classified
        if item["nps_group"] == "detractor" and item["annual_revenue_inr"] is not None
    )
    threshold = detractor_revenue[int(0.75 * (len(detractor_revenue) - 1))] if detractor_revenue else None
    candidates = []
    for item in classified:
        item_flags = flags.get(item["response_id"], [])
        contradiction = "POSSIBLE_SCORE_INTERPRETATION_ERROR" in item_flags
        revenue = item["annual_revenue_inr"]
        probability = settings.churn_for(item["nps_group"])
        expected = None if revenue is None or probability is None else revenue * probability
        high_value = threshold is not None and revenue is not None and item["nps_group"] == "detractor" and revenue >= threshold
        severe = item["primary_theme"] in SEVERE_THEMES and item["nps_group"] == "detractor"
        if not (high_value or item["switching_intent"] or contradiction or severe):
            continue
        reasons = []
        priority = 0
        if item["nps_group"] == "detractor":
            priority += 40
            reasons.append("The score is in the detractor range.")
        if item["switching_intent"]:
            priority += 30
            reasons.append("The comment describes an intention to move money or the relationship.")
        if contradiction:
            priority += 25
            reasons.append("The score and the comment disagree, so the response needs verification before it is used.")
        if high_value:
            priority += 20
            reasons.append("Annual revenue is at or above the 75th percentile of detractor revenue.")
        if severe:
            priority += 15
            reasons.append(f"The comment is classified as {item['primary_theme']}.")
        if item["switching_intent"] and item["nps_group"] == "detractor":
            timeframe = "TODAY"
        elif item["nps_group"] == "detractor" or contradiction:
            timeframe = "THIS_WEEK"
        else:
            timeframe = "MONITOR"
        if contradiction:
            action = "Verify whether the score or the comment was recorded incorrectly. Do not change either automatically."
        elif item["switching_intent"]:
            action = "A person should call, hear what would keep the relationship, and record the outcome. This system does not place the call."
        else:
            action = f"A person should call about the {item['primary_theme']} comment and confirm whether it is still unresolved."
        sentiment_risk = "HIGH" if item["nps_group"] == "detractor" else "MEDIUM" if contradiction else "LOW"
        candidates.append(
            {
                "response_id": item["response_id"],
                "product": item["product"],
                "score": item["score"],
                "annual_revenue_inr": revenue,
                "nps_classification": item["nps_group"],
                "theme": item["primary_theme"],
                "reason": " ".join(reasons),
                "priority_components": {
                    "customer_sentiment_risk": sentiment_risk,
                    "revenue_exposure_inr": revenue,
                    "expected_revenue_at_risk_inr": expected,
                    "data_quality_risk": "REVIEW" if item_flags else "NONE",
                    "data_quality_flags": item_flags,
                    "priority_score": priority,
                    "formula": "40 if detractor + 30 if switching intent + 25 if the score and comment disagree + 20 if high-value detractor + 15 if a severe detractor theme",
                },
                "suggested_action": action,
                "recommended_owner": THEME_OWNERS.get(item["primary_theme"], "Customer experience"),
                "timeframe": timeframe,
                "status": "RECOMMENDED",
            }
        )
    candidates.sort(key=lambda row: (-row["priority_components"]["priority_score"], -(row["annual_revenue_inr"] or 0), row["response_id"]))
    return candidates[: settings.callback_limit]
