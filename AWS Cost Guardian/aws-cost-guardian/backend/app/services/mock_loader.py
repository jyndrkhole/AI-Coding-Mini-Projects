"""Load checked-in demo fixtures. This module does not call AWS."""

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def mock_file(*parts: str) -> Path:
    return get_settings().resolved_mock_data_dir().joinpath(*parts)


def load_json(*parts: str) -> Any:
    path = mock_file(*parts)
    if not path.is_file():
        raise FileNotFoundError(f"Mock data file is missing: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
