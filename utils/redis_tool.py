# -*- coding: utf-8 -*-

from __future__ import annotations

import time

from config.settings import settings

try:
    import redis
except ImportError:  # pragma: no cover - used by the zero-dependency demo path.
    redis = None


class RedisClient:
    """Redis wrapper with an in-memory fallback for local demos."""

    _memory: dict[str, tuple[str, float | None]] = {}
    _pool = None

    def __init__(self):
        self._connection = None
        if redis is None:
            return
        try:
            if RedisClient._pool is None:
                RedisClient._pool = redis.ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=True,
                )
            self._connection = redis.Redis(connection_pool=RedisClient._pool)
            self._connection.ping()
        except Exception:
            self._connection = None

    def set(self, key, value, ex=None):
        if self._connection is not None:
            try:
                return self._connection.set(key, value, ex=ex)
            except Exception:
                pass
        expires_at = time.time() + ex if ex else None
        self._memory[key] = (value, expires_at)
        return True

    def get(self, key):
        if self._connection is not None:
            try:
                return self._connection.get(key)
            except Exception:
                pass
        item = self._memory.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at and expires_at < time.time():
            self._memory.pop(key, None)
            return None
        return value


if __name__ == "__main__":
    print(RedisClient().set("Testkey", "Simple Test", ex=10))
    print(RedisClient().get("Testkey"))
