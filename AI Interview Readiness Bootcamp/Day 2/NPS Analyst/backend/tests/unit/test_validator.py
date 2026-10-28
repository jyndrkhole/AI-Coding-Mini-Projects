"""Row validation keeps original values and reports problems."""

import pandas as pd

from app.data.normalizer import normalize
from app.data.validator import validate_frame


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def base(**overrides) -> dict:
    row = {
        "response_id": "R1",
        "date": "2026-07-15",
        "month": "2026-07",
        "product": "Savings Account",
        "tenure": "1-3 yrs",
        "channel": "Branch",
        "score": 9,
        "comment": "Fine",
        "annual_revenue_inr": 1000,
    }
    row.update(overrides)
    return row


def test_invalid_score_is_excluded_and_reported():
    result = validate_frame(frame([base(score=11), base(response_id="R2", score=8)]))
    assert result.valid_index == [1]
    assert any(issue.issue_type == "INVALID_SCORE" for issue in result.issues)
    assert normalize(frame([base(score=11), base(response_id="R2", score=8)]), result)[0].score == 8


def test_duplicate_id_keeps_the_first_row():
    result = validate_frame(frame([base(score=10), base(score=0)]))
    assert result.valid_index == [0]
    assert result.duplicate_ids_excluded == ["R1"]


def test_missing_comment_is_allowed():
    result = validate_frame(frame([base(comment=None)]))
    assert result.valid_index == [0]
    assert any(issue.issue_type == "EMPTY_COMMENT" for issue in result.issues)
    assert normalize(frame([base(comment=None)]), result)[0].comment is None


def test_pandas_missing_comment_is_not_stored_as_text():
    source = frame([base(comment=pd.NA)])
    result = validate_frame(source)
    assert result.valid_index == [0]
    assert any(issue.issue_type == "EMPTY_COMMENT" for issue in result.issues)
    assert normalize(source, result)[0].comment is None


def test_missing_revenue_is_not_treated_as_zero():
    result = validate_frame(frame([base(annual_revenue_inr=None)]))
    assert result.valid_index == [0]
    assert normalize(frame([base(annual_revenue_inr=None)]), result)[0].annual_revenue_inr is None


def test_month_mismatch_is_flagged_without_changing_the_column():
    source = frame([base(month="2026-08")])
    result = validate_frame(source)
    assert result.valid_index == [0]
    mismatch = next(issue for issue in result.issues if issue.issue_type == "MONTH_DATE_MISMATCH")
    assert mismatch.evidence["month_column"] == "2026-08"
    normalized = normalize(source, result)[0]
    assert normalized.month == "2026-08"
    assert normalized.analysis_month == "2026-07"


def test_invalid_date_is_excluded():
    result = validate_frame(frame([base(date="not-a-date")]))
    assert result.valid_index == []
    assert any(issue.issue_type == "INVALID_DATE" for issue in result.issues)
