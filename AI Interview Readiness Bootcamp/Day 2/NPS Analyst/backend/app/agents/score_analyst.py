"""How bad is the NPS position? Numbers are copied from tools."""

from __future__ import annotations

import asyncio

from app.agents import tools
from app.agents.prompts import SCORE_ANALYST
from app.analytics.confidence import stable_ranking


async def run() -> dict:
    await asyncio.sleep(0)
    overview = tools.get_nps_overview()
    monthly = tools.get_nps_by_month()
    segments = {name: tools.get_nps_by_segment(name) for name in ("product", "channel", "tenure")}
    confidence = {name: tools.get_confidence_analysis(name) for name in ("overall", "product", "channel", "tenure")}
    low_samples = []
    rankings = {}
    for name in ("product", "channel", "tenure"):
        rows = confidence[name].get("results", [])
        for row in rows:
            if row.get("low_sample"):
                low_samples.append({"segment_type": name, "segment": row["segment"], "sample_size": row["sample_size"], "caution": row["caution"]})
        rankings[name] = stable_ranking(rows)
    return {
        "agent": "ScoreAnalystAgent",
        "available": True,
        "question": "How bad is it?",
        "instructions": SCORE_ANALYST.strip(),
        "overview": {key: overview.get(key) for key in ("total_responses", "promoters", "passives", "detractors", "nps")},
        "alert": overview.get("alert"),
        "monthly": monthly["months"],
        "period": monthly["period"],
        "reference_claims": monthly["reference_claims"],
        "segments": {name: segments[name]["segments"] for name in segments},
        "low_samples": low_samples,
        "rankings": rankings,
        "tools_used": [
            "get_nps_overview",
            "get_nps_by_month",
            "get_nps_by_segment",
            "get_confidence_analysis",
        ],
    }
