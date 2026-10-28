"""Revenue exposure and expected revenue at risk. Neither figure is actual lost revenue."""

from __future__ import annotations

from collections import defaultdict

from app.core.config import Settings


def _blank_bucket(label: str, label_type: str) -> dict:
    return {
        "label": label,
        "label_type": label_type,
        "responses": 0,
        "revenue_exposed_inr": 0.0,
        "estimated_expected_revenue_at_risk_inr": 0.0,
        "missing_revenue_count": 0,
        "revenue_rows": 0,
    }


def _add(bucket: dict, revenue: float | None, probability: float | None) -> None:
    bucket["responses"] += 1
    if revenue is None or probability is None:
        bucket["missing_revenue_count"] += 1
        return
    bucket["revenue_rows"] += 1
    bucket["revenue_exposed_inr"] += revenue
    bucket["estimated_expected_revenue_at_risk_inr"] += revenue * probability


def _finish(bucket: dict) -> dict:
    total = bucket["responses"]
    bucket["coverage_percentage"] = (bucket["revenue_rows"] / total * 100) if total else None
    return bucket


def build_revenue(classified: list[dict], settings: Settings) -> dict:
    overall = _blank_bucket("all", "overall")
    by_group: dict[str, dict] = {}
    by_product: dict[str, dict] = {}
    by_channel: dict[str, dict] = {}
    by_tenure: dict[str, dict] = {}
    by_month: dict[str, dict] = {}
    by_theme: dict[str, dict] = {}
    per_response = []

    for item in classified:
        probability = settings.churn_for(item["nps_group"])
        revenue = item["annual_revenue_inr"]
        expected = None if revenue is None or probability is None else revenue * probability
        _add(overall, revenue, probability)
        for store, key, label_type in (
            (by_group, item["nps_group"], "nps_group"),
            (by_product, item["product"] or "Unknown", "product"),
            (by_channel, item["channel"] or "Unknown", "channel"),
            (by_tenure, item["tenure"] or "Unknown", "tenure"),
            (by_month, item["month"], "month"),
            (by_theme, item["primary_theme"], "theme"),
        ):
            store.setdefault(key, _blank_bucket(key, label_type))
            _add(store[key], revenue, probability)
        per_response.append(
            {
                "response_id": item["response_id"],
                "nps_group": item["nps_group"],
                "primary_theme": item["primary_theme"],
                "annual_revenue_inr": revenue,
                "churn_probability": probability,
                "revenue_exposed_inr": revenue,
                "estimated_expected_revenue_at_risk_inr": expected,
            }
        )

    def listing(store: dict[str, dict]) -> list[dict]:
        return [_finish(store[key]) for key in sorted(store)]

    finished = _finish(overall)
    assumptions = settings.assumptions()
    return {
        "revenue_exposed_inr": finished["revenue_exposed_inr"],
        "estimated_expected_revenue_at_risk_inr": finished["estimated_expected_revenue_at_risk_inr"],
        "assumptions": assumptions,
        "missing_revenue_count": finished["missing_revenue_count"],
        "coverage_percentage": finished["coverage_percentage"],
        "responses": finished["responses"],
        "by_group": listing(by_group),
        "by_product": listing(by_product),
        "by_channel": listing(by_channel),
        "by_tenure": listing(by_tenure),
        "by_month": listing(by_month),
        "by_theme": listing(by_theme),
        "per_response": per_response,
        "note": "Revenue exposed is annual revenue in the group. Expected revenue at risk multiplies that revenue by an assumed churn probability. Neither amount is actual lost revenue.",
    }


def high_value_detractors(classified: list[dict], settings: Settings, limit: int = 15) -> list[dict]:
    detractors = [item for item in classified if item["nps_group"] == "detractor" and item["annual_revenue_inr"] is not None]
    if not detractors:
        return []
    revenues = sorted(item["annual_revenue_inr"] for item in detractors)
    threshold = revenues[int(0.75 * (len(revenues) - 1))]
    ranked = []
    for item in detractors:
        probability = settings.churn_for("detractor")
        revenue = item["annual_revenue_inr"]
        if revenue < threshold and not item["switching_intent"]:
            continue
        ranked.append(
            {
                "response_id": item["response_id"],
                "score": item["score"],
                "annual_revenue_inr": revenue,
                "product": item["product"],
                "theme": item["primary_theme"],
                "month": item["month"],
                "switching_intent": item["switching_intent"],
                "revenue_exposed_inr": revenue,
                "estimated_expected_revenue_at_risk_inr": None if probability is None else revenue * probability,
                "high_value_threshold_inr": threshold,
            }
        )
    ranked.sort(key=lambda row: (-(row["estimated_expected_revenue_at_risk_inr"] or 0), row["response_id"]))
    return ranked[:limit]
