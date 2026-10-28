"""Paths and analysis settings. Secrets stay in the environment and are never returned by the API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_SURVEY_PATH = PROJECT_ROOT / "data" / "nps_survey.csv"
LOW_SAMPLE_LABEL = "LOW SAMPLE — INTERPRET WITH CAUTION"
MAX_UPLOAD_BYTES = 2_000_000

THEME_TAXONOMY = (
    "OTP_AND_LOGIN",
    "MOBILE_APP",
    "UPI_AND_PAYMENTS",
    "CUSTOMER_SUPPORT",
    "RELATIONSHIP_MANAGER",
    "FEES_AND_CHARGES",
    "WEALTH_ADVISORY",
    "ACCOUNT_ACCESS",
    "TRANSACTIONS",
    "SERVICE_QUALITY",
    "OTHER",
    "UNCLEAR",
)

# Higher means a more severe customer-experience failure. Used only for ranking, never as a measured loss.
DEFAULT_THEME_SEVERITY = {
    "OTP_AND_LOGIN": 5,
    "ACCOUNT_ACCESS": 5,
    "FEES_AND_CHARGES": 4,
    "CUSTOMER_SUPPORT": 4,
    "MOBILE_APP": 3,
    "UPI_AND_PAYMENTS": 3,
    "WEALTH_ADVISORY": 3,
    "TRANSACTIONS": 2,
    "RELATIONSHIP_MANAGER": 2,
    "SERVICE_QUALITY": 2,
    "OTHER": 1,
    "UNCLEAR": 1,
}

# Relative implementation effort. Customer-impact rank divides severity-weighted volume by this weight.
DEFAULT_THEME_COMPLEXITY = {
    "OTP_AND_LOGIN": 4,
    "ACCOUNT_ACCESS": 4,
    "MOBILE_APP": 3,
    "UPI_AND_PAYMENTS": 3,
    "FEES_AND_CHARGES": 3,
    "WEALTH_ADVISORY": 3,
    "CUSTOMER_SUPPORT": 2,
    "TRANSACTIONS": 2,
    "RELATIONSHIP_MANAGER": 2,
    "SERVICE_QUALITY": 2,
    "OTHER": 2,
    "UNCLEAR": 3,
}

THEME_OWNERS = {
    "OTP_AND_LOGIN": "Digital channels",
    "MOBILE_APP": "Digital channels",
    "UPI_AND_PAYMENTS": "Payments",
    "ACCOUNT_ACCESS": "Digital channels",
    "CUSTOMER_SUPPORT": "Customer care",
    "RELATIONSHIP_MANAGER": "Branch and RM operations",
    "FEES_AND_CHARGES": "Product",
    "WEALTH_ADVISORY": "Wealth",
    "TRANSACTIONS": "Payments",
    "SERVICE_QUALITY": "Customer experience",
    "OTHER": "Customer experience",
    "UNCLEAR": "Customer experience",
}

# Figures named in the assignment brief. Compared with the calculation and never written back as the result.
REFERENCE_NPS_CLAIMS = {"2026-07": 32.0, "2026-09": -6.5}


def survey_path() -> Path:
    configured = os.environ.get("NPS_SURVEY_PATH", "").strip()
    if not configured:
        return DEFAULT_SURVEY_PATH
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def database_url() -> str:
    configured = os.environ.get("NPS_DATABASE_URL", "").strip()
    if configured:
        return configured
    data_dir = BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'nps.db'}"


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


@dataclass
class Settings:
    churn_promoter: float = 0.03
    churn_passive: float = 0.10
    churn_detractor: float = 0.25
    bootstrap_samples: int = 1000
    bootstrap_seed: int = 42
    min_sample: int = 30
    critical_nps: float = 0.0
    severe_decline_points: float = 20.0
    mild_decline_points: float = 5.0
    callback_limit: int = 12
    theme_severity: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_THEME_SEVERITY))
    theme_complexity: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_THEME_COMPLEXITY))

    def churn_for(self, group: str) -> float | None:
        return {
            "promoter": self.churn_promoter,
            "passive": self.churn_passive,
            "detractor": self.churn_detractor,
        }.get(group)

    def assumptions(self) -> dict:
        return {
            "promoter_churn_probability": self.churn_promoter,
            "passive_churn_probability": self.churn_passive,
            "detractor_churn_probability": self.churn_detractor,
            "note": "Churn probabilities are planning assumptions, not measured attrition.",
        }

    def fingerprint(self) -> str:
        payload = {
            "churn_promoter": self.churn_promoter,
            "churn_passive": self.churn_passive,
            "churn_detractor": self.churn_detractor,
            "bootstrap_samples": self.bootstrap_samples,
            "bootstrap_seed": self.bootstrap_seed,
            "min_sample": self.min_sample,
            "critical_nps": self.critical_nps,
            "severe_decline_points": self.severe_decline_points,
            "mild_decline_points": self.mild_decline_points,
            "callback_limit": self.callback_limit,
            "theme_severity": self.theme_severity,
            "theme_complexity": self.theme_complexity,
        }
        return json.dumps(payload, sort_keys=True)


def get_settings() -> Settings:
    return Settings(
        churn_promoter=_float_env("NPS_CHURN_PROMOTER", 0.03),
        churn_passive=_float_env("NPS_CHURN_PASSIVE", 0.10),
        churn_detractor=_float_env("NPS_CHURN_DETRACTOR", 0.25),
        bootstrap_samples=_int_env("NPS_BOOTSTRAP_SAMPLES", 1000),
        bootstrap_seed=_int_env("NPS_BOOTSTRAP_SEED", 42),
        min_sample=_int_env("NPS_MIN_SAMPLE", 30),
        critical_nps=_float_env("NPS_CRITICAL_NPS", 0.0),
        severe_decline_points=_float_env("NPS_SEVERE_DECLINE", 20.0),
        mild_decline_points=_float_env("NPS_MILD_DECLINE", 5.0),
        callback_limit=_int_env("NPS_CALLBACK_LIMIT", 12),
    )


def llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip()) and os.environ.get("NPS_ENABLE_LLM", "").strip() == "true"


def model_name() -> str:
    return os.environ.get("NPS_MODEL", "gpt-4o").strip() or "gpt-4o"
