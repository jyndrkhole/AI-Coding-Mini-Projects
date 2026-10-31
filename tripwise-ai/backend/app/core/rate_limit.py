"""Small in-process window for expensive AI routes."""

import time

from fastapi import HTTPException, status

from app.core.config import get_settings

_buckets: dict[str, list[float]] = {}


def enforce_rate_limit(key: str) -> None:
    settings = get_settings()
    now = time.monotonic()
    window = settings.rate_limit_window_seconds
    recent = [stamp for stamp in _buckets.get(key, []) if now - stamp < window]
    if len(recent) >= settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Too many AI requests. Wait a moment and try again."},
        )
    recent.append(now)
    _buckets[key] = recent


def reset_rate_limits() -> None:
    _buckets.clear()
