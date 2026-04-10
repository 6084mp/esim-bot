from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheItem:
    value: Any
    expires_at: float


class InMemoryTTLCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl_seconds = ttl_seconds
        self._storage: dict[str, CacheItem] = {}

    def get(self, key: str) -> Any | None:
        item = self._storage.get(key)
        if not item:
            return None
        if item.expires_at < time.time():
            self._storage.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any) -> None:
        self._storage[key] = CacheItem(value=value, expires_at=time.time() + self._ttl_seconds)

    def invalidate(self, key: str) -> None:
        self._storage.pop(key, None)
