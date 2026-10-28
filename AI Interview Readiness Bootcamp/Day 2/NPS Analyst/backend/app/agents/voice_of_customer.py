"""Which comment themes moved with the score, using only tool evidence."""

from __future__ import annotations

import asyncio

from app.agents import tools
from app.agents.prompts import VOICE_OF_CUSTOMER


def _statement(themes: list[dict], period_change: float | None) -> dict:
    usable = [theme for theme in themes if theme["theme"] != "UNCLEAR" and theme.get("detractor_change") is not None]
    if not usable or period_change is None:
        return {"theme": None, "statement": "There is not enough monthly theme evidence to describe an association."}
    leader = max(usable, key=lambda theme: (theme["detractor_change"], theme["comments"], theme["theme"]))
    if period_change < 0 and leader["detractor_change"] > 0:
        text = (
            f"{leader['theme']} complaints were associated with the decline. "
            f"Detractor comments in that theme rose by {leader['detractor_change']} from the first month to the last. "
            "That is an association in the survey, not evidence that the theme caused the NPS change."
        )
    else:
        text = "No theme showed a rise in detractor comments alongside a fall in NPS. Frequency alone is not treated as a cause."
    return {"theme": leader["theme"], "detractor_change": leader["detractor_change"], "statement": text}


async def run() -> dict:
    await asyncio.sleep(0)
    themes_payload = tools.get_comment_themes()
    monthly = tools.get_nps_by_month()
    themes = themes_payload["themes"]
    association = _statement(themes, monthly["period"].get("period_nps_change"))
    negative = sorted(
        [theme for theme in themes if theme["theme"] != "UNCLEAR"],
        key=lambda theme: (-theme["detractors"], theme["theme"]),
    )[:3]
    positive = sorted(
        [theme for theme in themes if theme["theme"] != "UNCLEAR"],
        key=lambda theme: (-theme["promoters"], theme["theme"]),
    )[:3]
    quotes = []
    for theme in negative[:2]:
        tools.get_theme_by_month(theme["theme"])
        examples = tools.get_comment_examples(theme["theme"], "NEGATIVE", limit=2)["examples"]
        quotes.extend(examples)
    if positive:
        quotes.extend(tools.get_comment_examples(positive[0]["theme"], "POSITIVE", limit=1)["examples"])
    sentiment = tools.get_theme_sentiment_summary()
    return {
        "agent": "VoiceOfCustomerAgent",
        "available": True,
        "question": "Why did customer sentiment change?",
        "instructions": VOICE_OF_CUSTOMER.strip(),
        "themes": themes,
        "association": association,
        "negative_themes": negative,
        "positive_themes": positive,
        "quotes": quotes,
        "sentiment": sentiment["sentiments"],
        "priorities": themes_payload["priorities"],
        "tools_used": [
            "get_comment_themes",
            "get_nps_by_month",
            "get_theme_by_month",
            "get_comment_examples",
            "get_theme_sentiment_summary",
        ],
    }
