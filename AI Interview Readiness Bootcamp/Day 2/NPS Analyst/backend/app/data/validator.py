"""Validate rows and keep the original values. Invalid rows are reported, not rewritten."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.data.loader import REQUIRED_COLUMNS


@dataclass
class RowIssue:
    row_number: int
    response_id: str | None
    issue_type: str
    severity: str
    evidence: dict
    recommended_review: bool = True


@dataclass
class ValidationResult:
    original_rows: int
    issues: list[RowIssue] = field(default_factory=list)
    valid_index: list[int] = field(default_factory=list)
    duplicate_ids_excluded: list[str] = field(default_factory=list)

    @property
    def invalid_rows(self) -> int:
        return self.original_rows - len(self.valid_index)


def _text(value) -> str | None:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def validate_frame(frame: pd.DataFrame) -> ValidationResult:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Required columns are missing: {', '.join(missing)}")
    result = ValidationResult(original_rows=len(frame))
    seen_ids: set[str] = set()
    for position, row in frame.iterrows():
        row_number = int(position) + 2  # header is line 1
        response_id = _text(row.get("response_id"))
        blocking: list[RowIssue] = []

        if response_id is None:
            blocking.append(RowIssue(row_number, None, "MISSING_RESPONSE_ID", "HIGH", {}))
        elif response_id in seen_ids:
            issue = RowIssue(
                row_number,
                response_id,
                "DUPLICATE_RESPONSE_ID",
                "HIGH",
                {"response_id": response_id, "rule": "The first row with this id is kept. Later copies are excluded from NPS."},
            )
            result.issues.append(issue)
            result.duplicate_ids_excluded.append(response_id)
            continue
        else:
            seen_ids.add(response_id)

        score_raw = row.get("score")
        score_ok = False
        try:
            if pd.isna(score_raw):
                raise ValueError("missing")
            score = int(score_raw)
            if isinstance(score_raw, float) and not float(score_raw).is_integer():
                raise ValueError("fraction")
            if score < 0 or score > 10:
                raise ValueError("range")
            score_ok = True
        except (TypeError, ValueError):
            blocking.append(
                RowIssue(row_number, response_id, "INVALID_SCORE", "HIGH", {"score": None if pd.isna(score_raw) else score_raw})
            )

        date_raw = _text(row.get("date"))
        parsed = pd.to_datetime(date_raw, errors="coerce") if date_raw else pd.NaT
        if pd.isna(parsed):
            blocking.append(RowIssue(row_number, response_id, "INVALID_DATE", "HIGH", {"date": date_raw}))
        else:
            month_raw = _text(row.get("month"))
            derived = parsed.strftime("%Y-%m")
            if month_raw != derived:
                result.issues.append(
                    RowIssue(
                        row_number,
                        response_id,
                        "MONTH_DATE_MISMATCH",
                        "MEDIUM",
                        {"month_column": month_raw, "month_from_date": derived},
                    )
                )

        revenue_raw = row.get("annual_revenue_inr")
        if pd.isna(revenue_raw) or _text(revenue_raw) is None:
            result.issues.append(
                RowIssue(row_number, response_id, "MISSING_REVENUE", "MEDIUM", {"annual_revenue_inr": None})
            )
        else:
            try:
                revenue = float(revenue_raw)
                if revenue < 0:
                    blocking.append(
                        RowIssue(row_number, response_id, "NEGATIVE_REVENUE", "HIGH", {"annual_revenue_inr": revenue})
                    )
            except (TypeError, ValueError):
                blocking.append(
                    RowIssue(row_number, response_id, "INVALID_REVENUE", "HIGH", {"annual_revenue_inr": revenue_raw})
                )

        if _text(row.get("comment")) is None:
            result.issues.append(RowIssue(row_number, response_id, "EMPTY_COMMENT", "LOW", {}, recommended_review=False))

        for column in ("product", "tenure", "channel"):
            if _text(row.get(column)) is None:
                result.issues.append(
                    RowIssue(row_number, response_id, "MISSING_SEGMENT", "LOW", {"column": column})
                )

        result.issues.extend(blocking)
        if score_ok and not blocking:
            result.valid_index.append(int(position))
    return result
