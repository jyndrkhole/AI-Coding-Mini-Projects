"""What to fix, what to investigate, and who a person should call. No outreach is sent."""

from __future__ import annotations

from app.agents import tools
from app.agents.prompts import ACTION_PLANNER
from app.core.config import THEME_OWNERS


def _action(priority: int, kind: str, title: str, evidence: str, owner: str, timeframe: str, metric: str) -> dict:
    return {
        "priority": priority,
        "category": kind,
        "title": title,
        "evidence": evidence,
        "rationale": evidence,
        "suggested_owner": owner,
        "timeframe": timeframe,
        "success_metric": metric,
    }


async def run(score: dict, voice: dict, churn: dict) -> dict:
    priorities = tools.get_prioritized_themes()
    revenue = tools.get_revenue_at_risk()
    quality = tools.get_data_quality_summary()
    callbacks = tools.get_callback_candidates()
    impacts = []
    for row in priorities["customer_impact"][:2]:
        impacts.append(tools.estimate_fix_impact(row["theme"], "A"))
    actions = []
    if voice.get("available") and priorities["customer_impact"]:
        top = priorities["customer_impact"][0]
        actions.append(
            _action(
                1,
                "fix",
                f"Fix {top['theme']} first on customer impact",
                (
                    f"{top['theme']} has {top['detractors']} detractors and a customer-impact score of {top['customer_impact_score']:.2f}. "
                    f"The formula is {top['formula']}. Expected revenue at risk for the theme is ranked separately."
                ),
                top["owner"],
                "THIS_WEEK",
                "Fewer detractor comments in this theme and a higher NPS on the next month of responses.",
            )
        )
    elif not voice.get("available"):
        actions.append(
            _action(
                1,
                "fix",
                "Customer-impact narrative is unavailable",
                "The voice specialist did not finish, so this brief does not invent a theme story. The deterministic ranking is still listed below.",
                "Customer experience",
                "THIS_WEEK",
                "Rerun the voice specialist and confirm the theme ranking.",
            )
        )
    if priorities["revenue_at_risk"]:
        money = priorities["revenue_at_risk"][0]
        actions.append(
            _action(
                2,
                "investigate",
                f"Investigate {money['theme']} for expected revenue at risk",
                (
                    f"{money['theme']} leads expected revenue at risk at {money['expected_revenue_at_risk_inr']:.0f} rupees under the stated churn assumptions. "
                    f"The highest-volume theme is {priorities['highest_volume_theme']}. "
                    + (
                        "Those are the same theme."
                        if priorities["same_theme"]
                        else "Those are different themes, so volume and revenue justify different work."
                    )
                ),
                THEME_OWNERS.get(money["theme"], "Product"),
                "THIS_WEEK",
                "A reviewed list of high-revenue responses in this theme, with revenue still excluded where it is missing.",
            )
        )
    actions.append(
        _action(
            3,
            "monitor",
            "Verify contradictory scores and watch the next survey month",
            (
                f"{quality['contradiction_count']} responses have a score that conflicts with the comment. "
                f"{quality['missing_comment_count']} comments are blank. Scores were not changed."
            ),
            "Customer experience",
            "MONITOR",
            "Contradictory rows are reviewed, and the following month's NPS is calculated the same way.",
        )
    )
    return {
        "agent": "ActionPlannerAgent",
        "available": True,
        "question": "What should we fix first, and who should receive a callback?",
        "instructions": ACTION_PLANNER.strip(),
        "used_specialists": {
            "score": score.get("available", False),
            "voice": voice.get("available", False),
            "churn": churn.get("available", False),
        },
        "customer_impact": priorities["customer_impact"],
        "revenue_at_risk_ranking": priorities["revenue_at_risk"],
        "low_sample_themes": priorities["low_sample_themes"],
        "same_theme": priorities["same_theme"],
        "highest_volume_theme": priorities["highest_volume_theme"],
        "highest_expected_revenue_theme": priorities["highest_expected_revenue_theme"],
        "fix_impacts": impacts,
        "actions": actions,
        "callbacks": callbacks["candidates"],
        "assumptions": revenue["assumptions"],
        "tradeoff": priorities["note"],
        "tools_used": [
            "get_prioritized_themes",
            "estimate_fix_impact",
            "get_callback_candidates",
            "get_revenue_at_risk",
            "get_data_quality_summary",
        ],
    }
