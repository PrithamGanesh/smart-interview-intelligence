"""Redis cache adapter with an in-memory fallback for local development."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.core.config import get_settings

try:
    import redis
except ImportError:  # pragma: no cover - optional production dependency
    redis = None


class Cache:
    """Small cache facade used by services."""

    def __init__(self) -> None:
        self._memory: dict[str, str] = {}
        self._client = None
        if redis is not None:
            try:
                self._client = redis.from_url(get_settings().redis_url, decode_responses=True)
            except Exception:
                self._client = None

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._client.get(key) if self._client else self._memory.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        raw = json.dumps(value)
        if self._client:
            self._client.setex(key, ttl_seconds, raw)
        else:
            self._memory[key] = raw


cache = Cache()
