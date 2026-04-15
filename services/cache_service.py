from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class CacheService:
    def __init__(self) -> None:
        self._storage: dict[str, CacheItem] = {}

    def get(self, key: str) -> Any | None:
        item = self._storage.get(key)
        if not item:
            return None
        if item.expires_at < time.time():
            self._storage.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._storage[key] = CacheItem(value=value, expires_at=time.time() + max(1, ttl))

    def delete(self, key: str) -> None:
        self._storage.pop(key, None)
