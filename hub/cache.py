import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Cache TTLs in seconds, keyed by domain
CACHE_TTL: dict[str, int] = {
    "weather": 300,          # 5 min
    "calendar_today": 120,   # 2 min
    "calendar_week": 300,    # 5 min
    "tasks": 120,            # 2 min
    "email_summary": 180,    # 3 min
    "dashboard": 60,         # 1 min
}


class RedisCache:
    """Thin async Redis abstraction used throughout the hub."""

    def __init__(self, redis_url: str) -> None:
        self._client: aioredis.Redis = aioredis.from_url(  # type: ignore[no-untyped-call]
            redis_url, encoding="utf-8", decode_responses=True
        )

    async def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or None if missing/expired."""
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.exception("Cache GET failed for key=%s", key)
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* with a TTL in seconds."""
        try:
            await self._client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            logger.exception("Cache SET failed for key=%s", key)

    async def invalidate(self, key: str) -> None:
        """Delete *key* from the cache."""
        try:
            await self._client.delete(key)
        except Exception:
            logger.exception("Cache INVALIDATE failed for key=%s", key)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys matching *prefix*:*."""
        try:
            keys = await self._client.keys(f"{prefix}:*")
            if keys:
                await self._client.delete(*keys)
        except Exception:
            logger.exception("Cache INVALIDATE_PREFIX failed for prefix=%s", prefix)

    async def health_check(self) -> bool:
        """Return True if Redis responds to PING."""
        try:
            return bool(await self._client.ping())
        except Exception:
            logger.exception("Redis health check failed")
            return False

    async def close(self) -> None:
        await self._client.aclose()
