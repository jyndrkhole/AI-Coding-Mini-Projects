"""Bootstrap percentile intervals for NPS. The seed is part of the configuration so a rerun matches."""

from __future__ import annotations

import zlib

import numpy as np

from app.analytics.nps import calculate_nps
from app.analytics.segmentation import SEGMENT_FIELDS, group_responses
from app.analytics.trends import with_changes
from app.core.config import LOW_SAMPLE_LABEL, Settings
from app.data.normalizer import NormalizedResponse


def _coded(responses: list[NormalizedResponse]) -> np.ndarray:
    values = []
    for row in responses:
        if row.score >= 9:
            values.append(1.0)
        elif row.score >= 7:
            values.append(0.0)
        else:
            values.append(-1.0)
    return np.asarray(values, dtype=float)


def _seed_for(name: str, base_seed: int) -> int:
    return (base_seed + zlib.adler32(name.encode("utf-8"))) % (2**32)


def bootstrap_interval(responses: list[NormalizedResponse], settings: Settings, seed_name: str) -> dict:
    """95% interval from the 2.5 and 97.5 percentiles of bootstrap NPS replicates.

    Each response is coded +1 promoter, 0 passive, -1 detractor. The mean of that code times 100
    is the NPS, so resampling responses and taking the mean estimates the sampling interval.
    """
    point = calculate_nps(responses)
    n = point["total_responses"]
    base = {
        "method": "bootstrap percentile",
        "level": 0.95,
        "samples": settings.bootstrap_samples,
        "seed": _seed_for(seed_name, settings.bootstrap_seed),
        "sample_size": n,
        "low_sample": n < settings.min_sample,
        "caution": LOW_SAMPLE_LABEL if n < settings.min_sample else None,
    }
    if n == 0:
        return {**base, "low": None, "high": None}
    coded = _coded(responses)
    if n == 1:
        value = float(coded[0] * 100)
        return {**base, "low": value, "high": value}
    rng = np.random.default_rng(base["seed"])
    draws = rng.integers(0, n, size=(settings.bootstrap_samples, n))
    estimates = coded[draws].mean(axis=1) * 100
    low, high = np.percentile(estimates, [2.5, 97.5])
    return {**base, "low": float(low), "high": float(high)}


def _with_interval(summary: dict, responses: list[NormalizedResponse], settings: Settings, seed_name: str) -> dict:
    interval = bootstrap_interval(responses, settings, seed_name)
    merged = dict(summary)
    merged.update(
        {
            "confidence_low": interval["low"],
            "confidence_high": interval["high"],
            "confidence_method": interval["method"],
            "low_sample": interval["low_sample"],
            "caution": interval["caution"],
            "sample_size": interval["sample_size"],
        }
    )
    return merged


def build_confidence(responses: list[NormalizedResponse], settings: Settings) -> dict:
    months = []
    by_month: dict[str, list[NormalizedResponse]] = {}
    for row in responses:
        by_month.setdefault(row.analysis_month, []).append(row)
    for summary in with_changes(responses):
        members = by_month.get(summary["month"], [])
        months.append(_with_interval(summary, members, settings, f"month:{summary['month']}"))

    segments: dict[str, list[dict]] = {}
    for field in SEGMENT_FIELDS:
        rows = []
        grouped = group_responses(responses, field)
        for summary_seed in sorted(grouped):
            summary = calculate_nps(grouped[summary_seed])
            summary["segment"] = summary_seed
            summary["segment_type"] = field
            rows.append(_with_interval(summary, grouped[summary_seed], settings, f"{field}:{summary_seed}"))
        segments[field] = rows

    return {
        "overall": _with_interval(calculate_nps(responses), responses, settings, "overall"),
        "months": months,
        "segments": segments,
        "minimum_sample": settings.min_sample,
        "ranking_note": (
            "A segment below the minimum sample is labelled and is not treated as definitively best or worst."
        ),
    }


def stable_ranking(rows: list[dict]) -> dict:
    stable = [row for row in rows if not row.get("low_sample")]
    caution = [row for row in rows if row.get("low_sample")]
    ordered = sorted(stable, key=lambda row: (row.get("nps") is None, row.get("nps") if row.get("nps") is not None else 0))
    return {
        "ranked": ordered,
        "low_sample": caution,
        "note": "Low-sample segments are shown separately and are not ranked as the best or worst result.",
    }
