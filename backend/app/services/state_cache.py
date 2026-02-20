from __future__ import annotations

import json
import os
from typing import Any


class StateCache:
    """Redis-first cache with in-memory fallback."""

    def __init__(self) -> None:
        self._memory: dict[str, Any] = {}
        self._redis = None
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

        try:
            import redis

            self._redis = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )
            self._redis.ping()
        except Exception:
            self._redis = None

    def set_json(self, key: str, value: Any) -> None:
        if self._redis:
            self._redis.set(key, json.dumps(value))
            return
        self._memory[key] = value

    def get_json(self, key: str, default: Any = None) -> Any:
        if self._redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else default
        return self._memory.get(key, default)
