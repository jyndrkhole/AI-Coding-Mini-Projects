"""Keyword theme and sentiment baseline. An unknown model label is rejected rather than added to the taxonomy."""

from __future__ import annotations

from collections import defaultdict
import re

from app.analytics.nps import calculate_nps, classify_score
from app.core.config import THEME_TAXONOMY
from app.data.normalizer import NormalizedResponse

POSITIVE_PHRASES = (
    "excellent",
    "love the",
    "love it",
    "amazing",
    "thank you",
    "super quick",
    "are quick",
    "easy to use",
    "smooth",
    "fully online",
    "feel safe",
    "are fast",
    "helpful",
    "no complaints",
    "happy with",
    "very happy",
    "seamless",
    "great cashback",
    "actually useful",
    "no pushy",
    "always picks up",
    "sorted my",
    "best bank",
    "solves the problem",
    "otherwise fine",
    "otherwise okay",
    "works now",
    "decent",
    "works",
)

NEGATIVE_PHRASES = (
    "not happy",
    "poor",
    "frustrating",
    "crashes",
    "crash",
    "broken",
    "never arrives",
    "never reached",
    "never comes",
    "does not come",
    "fails",
    "locked out",
    "slow",
    "hangs",
    "glitches",
    "glitch",
    "freezes",
    "on hold",
    "circles",
    "moving my",
    "thinking of moving",
    "expire",
    "confusing",
    "penalty",
    "hidden cost",
    "charges",
    "charged",
    "fee",
    "could be better",
    "lower than",
    "earns more",
    "waiting time",
    "a day late",
    "call dropped",
    "could not login",
    "couldn't get into",
    "logging me out",
    "was a problem",
    "delayed",
    "too quickly",
    "not fixed",
    "paying so much",
    "never get",
    "had to wait",
)

THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("OTP_AND_LOGIN", ("otp", "verification code", "code that never comes", "login", "locked out", "logging me out", "get into my account", "couldn't get into")),
    ("FEES_AND_CHARGES", ("fee", "charge", "hidden cost", "penalty", "paying so much")),
    ("WEALTH_ADVISORY", ("wealth", "portfolio", "advice", "fd")),
    ("CUSTOMER_SUPPORT", ("customer care", "ivr", "call centre", "callback", "on hold", "call dropped")),
    ("RELATIONSHIP_MANAGER", ("relationship manager", "my rm")),
    ("UPI_AND_PAYMENTS", ("upi", "recharge", "bill payment")),
    ("MOBILE_APP", ("app", "glitch", "freeze", "crash", "statements page")),
    ("ACCOUNT_ACCESS", ("opening the account", "kyc", "check my balance")),
    ("TRANSACTIONS", ("transfer",)),
)

SWITCHING_PHRASES = ("moving my", "thinking of moving")


def sentiment_of(comment: str | None) -> str:
    if comment is None or not comment.strip():
        return "UNKNOWN"
    text = comment.lower()
    positive = False
    for phrase in POSITIVE_PHRASES:
        if phrase in {"happy with", "very happy"} and "not happy" in text:
            continue
        if _contains(text, phrase):
            positive = True
            break
    negative = any(_contains(text, phrase) for phrase in NEGATIVE_PHRASES)
    if positive and negative:
        return "MIXED"
    if positive:
        return "POSITIVE"
    if negative:
        return "NEGATIVE"
    return "NEUTRAL"


def switching_intent(comment: str | None) -> bool:
    if not comment:
        return False
    text = comment.lower()
    return any(phrase in text for phrase in SWITCHING_PHRASES)


def _contains(text: str, phrase: str) -> bool:
    # "recharge" contains "charge" but it is a payment word, not a fee.
    if phrase == "charge":
        return re.search(r"(?<!re)charge", text) is not None
    return phrase in text


def _matching_themes(text: str) -> list[tuple[str, str]]:
    found = []
    for theme, phrases in THEME_RULES:
        for phrase in phrases:
            if _contains(text, phrase):
                found.append((theme, phrase))
                break
    return found


def classify_comment(comment: str | None) -> dict:
    if comment is None or not comment.strip():
        return {
            "primary_theme": "UNCLEAR",
            "secondary_theme": None,
            "sentiment": "UNKNOWN",
            "confidence": 0.0,
            "evidence_phrase": None,
            "classification_source": "keyword",
            "switching_intent": False,
        }
    text = comment.lower()
    matches = _matching_themes(text)
    sentiment = sentiment_of(comment)
    if matches:
        primary, evidence = matches[0]
        secondary = matches[1][0] if len(matches) > 1 else None
        confidence = 0.9
    elif sentiment == "NEUTRAL":
        primary, secondary, evidence, confidence = "UNCLEAR", None, None, 0.3
    else:
        primary, secondary, evidence, confidence = "SERVICE_QUALITY", None, None, 0.62
    return {
        "primary_theme": primary,
        "secondary_theme": secondary,
        "sentiment": sentiment,
        "confidence": confidence,
        "evidence_phrase": evidence,
        "classification_source": "keyword",
        "switching_intent": switching_intent(comment),
    }


def accept_model_theme(label: str | None) -> str:
    """Reject a label that is not in the configured taxonomy."""
    if label in THEME_TAXONOMY:
        return label
    return "UNCLEAR"


def classify_responses(responses: list[NormalizedResponse]) -> list[dict]:
    classified = []
    for row in responses:
        item = classify_comment(row.comment)
        item["response_id"] = row.response_id
        item["score"] = row.score
        item["nps_group"] = classify_score(row.score)
        item["month"] = row.analysis_month
        item["product"] = row.product
        item["channel"] = row.channel
        item["tenure"] = row.tenure
        item["annual_revenue_inr"] = row.annual_revenue_inr
        item["comment"] = row.comment
        classified.append(item)
    return classified


def _theme_record(theme: str, members: list[dict], months: list[str] | None = None) -> dict:
    class _Row:
        def __init__(self, score: int):
            self.score = score

    nps_rows = [_Row(item["score"]) for item in members]
    summary = calculate_nps(nps_rows)  # type: ignore[arg-type]
    revenues = [item["annual_revenue_inr"] for item in members if item["annual_revenue_inr"] is not None]
    by_month: dict[str, list[dict]] = defaultdict(list)
    for item in members:
        by_month[item["month"]].append(item)
    monthly = []
    for month in sorted(by_month):
        bucket = by_month[month]
        month_nps = calculate_nps([_Row(item["score"]) for item in bucket])  # type: ignore[arg-type]
        monthly.append(
            {
                "month": month,
                "comments": len(bucket),
                "detractors": month_nps["detractors"],
                "promoters": month_nps["promoters"],
                "nps": month_nps["nps"],
            }
        )
    detractor_change = None
    month_counts = {row["month"]: row["detractors"] for row in monthly}
    if months and len(months) >= 2:
        detractor_change = month_counts.get(months[-1], 0) - month_counts.get(months[0], 0)
    elif len(monthly) >= 2:
        detractor_change = monthly[-1]["detractors"] - monthly[0]["detractors"]
    return {
        "theme": theme,
        "comments": len(members),
        "unique_responses": len({item["response_id"] for item in members}),
        "promoters": summary["promoters"],
        "passives": summary["passives"],
        "detractors": summary["detractors"],
        "nps": summary["nps"],
        "average_score": (sum(item["score"] for item in members) / len(members)) if members else None,
        "annual_revenue_inr": sum(revenues) if revenues else None,
        "revenue_responses": len(revenues),
        "missing_revenue_count": len(members) - len(revenues),
        "monthly": monthly,
        "detractor_change": detractor_change,
    }


def aggregate_themes(classified: list[dict], months: list[str] | None = None) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in classified:
        grouped[item["primary_theme"]].append(item)
    records = [_theme_record(theme, members, months) for theme, members in grouped.items()]
    return sorted(records, key=lambda record: (-record["comments"], record["theme"]))


def examples_for(classified: list[dict], theme: str, sentiment: str | None, limit: int = 3) -> list[dict]:
    rows = []
    for item in classified:
        if item["primary_theme"] != theme:
            continue
        if sentiment and item["sentiment"] != sentiment:
            continue
        if not item.get("comment"):
            continue
        rows.append(
            {
                "response_id": item["response_id"],
                "comment": item["comment"],
                "score": item["score"],
                "month": item["month"],
                "sentiment": item["sentiment"],
                "theme": item["primary_theme"],
            }
        )
    return rows[:limit]
