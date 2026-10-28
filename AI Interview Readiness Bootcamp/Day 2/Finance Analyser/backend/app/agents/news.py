"""Headline sentiment. Lexicon first; the model may relabel only articles that were retrieved."""

from __future__ import annotations

import asyncio
import json

from app.domain.models import CompanySnapshot, NewsArticle, NewsResult, SentimentLabel
from app.llm import LLMClient

POSITIVE = (
    "beat",
    "beats",
    "record",
    "surge",
    "upgrade",
    "raises guidance",
    "raised guidance",
    "strong demand",
    "profit rose",
    "outperform",
    "breakthrough",
)
NEGATIVE = (
    "miss",
    "misses",
    "lawsuit",
    "probe",
    "downgrade",
    "recall",
    "fraud",
    "cuts guidance",
    "cut guidance",
    "profit fell",
    "investigation",
    "slump",
    "layoff",
    "layoffs",
    "fine",
)
CATEGORIES = (
    ("legal", ("lawsuit", "regulator", "investigation", "antitrust", "probe", "fine")),
    ("management", ("ceo", "cfo", "resign", "appointed", "steps down")),
    ("analyst", ("upgrade", "downgrade", "price target", "analyst")),
    ("earnings", ("earnings", "revenue", "eps", "profit", "guidance", "quarter")),
    ("product", ("launch", "recall", "product")),
    ("macro", ("inflation", "recession", "interest rate")),
)
SCORES = {"STRONGLY_BULLISH": 2, "BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1, "STRONGLY_BEARISH": -2}


def categorize(text: str) -> str:
    lowered = text.lower()
    for name, words in CATEGORIES:
        if any(word in lowered for word in words):
            return name
    return "other"


def lexicon_score(text: str) -> int:
    lowered = text.lower()
    score = sum(1 for word in POSITIVE if word in lowered) - sum(1 for word in NEGATIVE if word in lowered)
    return max(-2, min(2, score))


def label_from_score(score: float) -> SentimentLabel:
    if score >= 1.5:
        return "STRONGLY_BULLISH"
    if score >= 0.4:
        return "BULLISH"
    if score > -0.4:
        return "NEUTRAL"
    if score > -1.5:
        return "BEARISH"
    return "STRONGLY_BEARISH"


def prepare_articles(articles: list[NewsArticle], snapshot: CompanySnapshot) -> list[NewsArticle]:
    import re

    stop = {"inc", "corp", "ltd", "limited", "company", "group", "plc", "holdings", "the"}
    name_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+", snapshot.market.company_name)
        if len(token) > 3 and token.lower() not in stop
    ]
    ticker_token = snapshot.market.ticker.split(".")[0].lower()
    prepared = []
    for article in articles:
        text = f"{article.title} {article.summary or ''}"
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        score = lexicon_score(text)
        mentions = ticker_token in tokens or any(part in tokens for part in name_tokens)
        prepared.append(
            article.model_copy(
                update={
                    "category": categorize(text),
                    "sentiment": label_from_score(score),
                    "sentiment_reason": f"Lexicon score {score} on the headline and summary.",
                    "mentions_company": mentions,
                }
            )
        )
    return prepared


def overall_label(articles: list[NewsArticle]) -> SentimentLabel:
    relevant = [article for article in articles if article.mentions_company] or articles
    if not relevant:
        return "INSUFFICIENT_DATA"
    average = sum(SCORES[article.sentiment] for article in relevant) / len(relevant)
    return label_from_score(average)


class NewsAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, articles: list[NewsArticle], snapshot: CompanySnapshot, lookback_days: int) -> NewsResult:
        await asyncio.sleep(0)
        if not articles:
            return NewsResult(
                label="INSUFFICIENT_DATA",
                lookback_days=lookback_days,
                method="unavailable",
                limitations=["No news articles were returned for this ticker and lookback. None were invented."],
                confidence="INSUFFICIENT",
            )
        prepared = prepare_articles(articles, snapshot)
        specific = [article for article in prepared if article.mentions_company]
        if len(specific) >= 2:
            prepared = specific
        method = "lexicon"
        limitations = [
            "Headlines come from Yahoo Finance. When Ticker.news is empty, the same vendor's search feed is used.",
            "Sentiment is a reading of headlines. It is not a forecast, and a positive headline is not evidence that the fundamentals improved.",
        ]
        if not any(article.mentions_company for article in prepared):
            limitations.append("No article clearly names the company. The label uses the retrieved set anyway and confidence is low.")
        if self.llm.configured:
            reviewed = await self._relabel(prepared)
            if reviewed:
                prepared = reviewed
                method = "llm"
        positives = [article.title for article in prepared if article.sentiment in {"BULLISH", "STRONGLY_BULLISH"}][:5]
        negatives = [article.title for article in prepared if article.sentiment in {"BEARISH", "STRONGLY_BEARISH"}][:5]
        confidence = "MEDIUM" if method == "llm" else "LOW"
        if len(prepared) < 2:
            confidence = "LOW"
        return NewsResult(
            label=overall_label(prepared),
            lookback_days=lookback_days,
            articles=prepared,
            catalysts_positive=positives,
            catalysts_negative=negatives,
            method=method,  # type: ignore[arg-type]
            limitations=limitations,
            confidence=confidence,  # type: ignore[arg-type]
        )

    async def _relabel(self, articles: list[NewsArticle]) -> list[NewsArticle] | None:
        payload = [
            {"id": article.id, "title": article.title, "summary": article.summary, "publisher": article.publisher}
            for article in articles[:12]
        ]
        system = (
            "Classify each supplied article. Return JSON {\"articles\": [{\"id\", \"sentiment\", \"reason\"}]}. "
            "sentiment must be STRONGLY_BULLISH, BULLISH, NEUTRAL, BEARISH, or STRONGLY_BEARISH. "
            "Do not add articles. Do not invent dates or numbers. A reason must refer to the title."
        )
        parsed = await self.llm.complete_json(system, json.dumps(payload))
        if not parsed or not isinstance(parsed.get("articles"), list):
            return None
        by_id = {article.id: article for article in articles}
        allowed = set(SCORES)
        for row in parsed["articles"]:
            if not isinstance(row, dict) or row.get("id") not in by_id:
                continue
            sentiment = row.get("sentiment")
            if sentiment not in allowed:
                continue
            current = by_id[row["id"]]
            by_id[row["id"]] = current.model_copy(
                update={
                    "sentiment": sentiment,
                    "sentiment_reason": str(row.get("reason") or "Model classification of the supplied headline."),
                }
            )
        return list(by_id.values())


def empty_news(lookback_days: int, reason: str) -> NewsResult:
    return NewsResult(
        label="INSUFFICIENT_DATA",
        lookback_days=lookback_days,
        method="unavailable",
        limitations=[reason],
        confidence="INSUFFICIENT",
    )
