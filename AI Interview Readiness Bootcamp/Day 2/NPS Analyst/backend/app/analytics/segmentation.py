"""NPS by product, channel, and tenure. Unknown labels stay visible."""

from __future__ import annotations

from collections import defaultdict

from app.analytics.nps import calculate_nps
from app.data.normalizer import NormalizedResponse

SEGMENT_FIELDS = ("product", "channel", "tenure")


def group_responses(responses: list[NormalizedResponse], field: str) -> dict[str, list[NormalizedResponse]]:
    grouped: dict[str, list[NormalizedResponse]] = defaultdict(list)
    for row in responses:
        label = getattr(row, field) or "Unknown"
        grouped[label].append(row)
    return grouped


def segment_summaries(responses: list[NormalizedResponse], field: str) -> list[dict]:
    if field not in SEGMENT_FIELDS:
        raise ValueError(f"segment field must be one of {', '.join(SEGMENT_FIELDS)}")
    grouped = group_responses(responses, field)
    summaries = []
    for label in sorted(grouped):
        summary = calculate_nps(grouped[label])
        summary["segment"] = label
        summary["segment_type"] = field
        summaries.append(summary)
    return summaries


def build_segments(responses: list[NormalizedResponse]) -> dict[str, list[dict]]:
    return {field: segment_summaries(responses, field) for field in SEGMENT_FIELDS}
