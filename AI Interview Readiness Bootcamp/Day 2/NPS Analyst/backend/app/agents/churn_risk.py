"""Revenue exposure, expected revenue at risk, and whether the inputs are trustworthy."""

from __future__ import annotations

import asyncio

from app.agents import tools
from app.agents.prompts import CHURN_RISK


async def run() -> dict:
    await asyncio.sleep(0)
    revenue = tools.get_revenue_at_risk()
    by_product = tools.get_revenue_by_segment("product")
    by_theme = tools.get_revenue_by_segment("theme")
    by_group = tools.get_revenue_by_segment("nps_group")
    detractors = tools.find_high_value_detractors()
    mismatches = tools.find_score_comment_mismatches()
    quality = tools.get_data_quality_summary()
    priorities = tools.get_prioritized_themes()
    return {
        "agent": "ChurnRiskAgent",
        "available": True,
        "question": "How much money is at risk, and can we trust the numbers?",
        "instructions": CHURN_RISK.strip(),
        "revenue_exposed_inr": revenue["revenue_exposed_inr"],
        "estimated_expected_revenue_at_risk_inr": revenue["estimated_expected_revenue_at_risk_inr"],
        "assumptions": revenue["assumptions"],
        "missing_revenue_count": revenue["missing_revenue_count"],
        "coverage_percentage": revenue["coverage_percentage"],
        "by_product": by_product["rows"],
        "by_theme": by_theme["rows"],
        "by_group": by_group["rows"],
        "high_value_detractors": detractors["customers"],
        "mismatches": mismatches,
        "data_quality": quality,
        "volume_leader": priorities["highest_volume_theme"],
        "revenue_leader": priorities["highest_expected_revenue_theme"],
        "volume_and_revenue_same_theme": priorities["same_theme"],
        "statement": (
            "Revenue exposed is the annual revenue on the survey responses. "
            "Expected revenue at risk multiplies that revenue by the configured churn assumption for the NPS group. "
            "The probabilities are not measured attrition, and neither figure is actual lost revenue. "
            "Missing revenue is excluded from both sums."
        ),
        "tools_used": [
            "get_revenue_at_risk",
            "get_revenue_by_segment",
            "find_high_value_detractors",
            "find_score_comment_mismatches",
            "get_data_quality_summary",
            "get_prioritized_themes",
        ],
    }
