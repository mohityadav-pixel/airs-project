"""Small in-process TTL cache + last-known-good store.

Upstream AQI/weather APIs are rate-limited; AIRS must not hammer them on
every page load. The last-known-good store additionally lets the API keep
serving *clearly time-stamped* recent data when an upstream call fails,
instead of showing the user an empty screen.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _Entry:
    value: Any
    expires_at: float
    stored_at: float


class TTLCache:
    def __init__(self) -> None:
        self._data: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.expires_at > time.time():
                return entry.value
            return None

    def get_stale(self, key: str) -> tuple[Any, float] | None:
        """Return a value even if expired, with the epoch it was stored at."""
        with self._lock:
            entry = self._data.get(key)
            return (entry.value, entry.stored_at) if entry else None

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            now = time.time()
            self._data[key] = _Entry(value, now + ttl_seconds, now)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


cache = TTLCache()


def cached_call(key: str, ttl_seconds: float, fn: Callable[[], Any]) -> Any:
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = fn()
    cache.set(key, value, ttl_seconds)
    return value
