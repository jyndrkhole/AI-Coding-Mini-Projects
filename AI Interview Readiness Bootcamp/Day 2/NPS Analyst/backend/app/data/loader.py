"""Load a survey CSV without inventing rows when the file is missing."""

from pathlib import Path

import pandas as pd

from app.core.exceptions import DatasetNotFound, DatasetSchemaError

REQUIRED_COLUMNS = (
    "response_id",
    "date",
    "month",
    "product",
    "tenure",
    "channel",
    "score",
    "comment",
    "annual_revenue_inr",
)


def load_survey_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DatasetNotFound(
            f"Survey file not found at {path}. Upload a CSV with the required columns. No sample rows were invented."
        )
    try:
        frame = pd.read_csv(path, dtype={"response_id": "string", "comment": "string"})
    except pd.errors.ParserError as exc:
        raise DatasetSchemaError(f"The CSV could not be parsed: {exc}") from exc
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DatasetSchemaError(f"Required columns are missing: {', '.join(missing)}")
    return frame
