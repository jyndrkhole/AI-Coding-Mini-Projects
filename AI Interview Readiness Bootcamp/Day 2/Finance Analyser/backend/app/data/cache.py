"""In-memory TTL cache so a second agent does not pay for the same Yahoo request."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, object]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        async with self._lock:
            hit = self._items.get(key)
            if hit and now - hit[0] < self.ttl_seconds:
                return hit[1]  # type: ignore[return-value]
        value = await factory()
        async with self._lock:
            self._items[key] = (time.monotonic(), value)
        return value
