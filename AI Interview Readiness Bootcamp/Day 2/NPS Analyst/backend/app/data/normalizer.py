"""Normalized analysis rows. Original column values are copied, not corrected."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.data.validator import ValidationResult, _text


@dataclass
class NormalizedResponse:
    response_id: str
    date: str
    month: str
    analysis_month: str
    product: str | None
    tenure: str | None
    channel: str | None
    score: int
    comment: str | None
    annual_revenue_inr: float | None


def normalize(frame: pd.DataFrame, validation: ValidationResult) -> list[NormalizedResponse]:
    rows: list[NormalizedResponse] = []
    for position in validation.valid_index:
        source = frame.loc[position]
        parsed = pd.to_datetime(_text(source["date"]))
        revenue_raw = source["annual_revenue_inr"]
        revenue = None if pd.isna(revenue_raw) else float(revenue_raw)
        rows.append(
            NormalizedResponse(
                response_id=_text(source["response_id"]) or "",
                date=parsed.date().isoformat(),
                month=_text(source["month"]) or "",
                analysis_month=parsed.strftime("%Y-%m"),
                product=_text(source["product"]),
                tenure=_text(source["tenure"]),
                channel=_text(source["channel"]),
                score=int(source["score"]),
                comment=_text(source["comment"]),
                annual_revenue_inr=revenue,
            )
        )
    return rows
