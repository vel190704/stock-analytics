"""Redis caching service.

Provides typed get/set/exists helpers with automatic JSON serialisation
and configurable TTL.  All operations are async.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class _CustomEncoder(json.JSONEncoder):
    """Serialise types that stdlib json cannot handle."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class CacheService:
    """Async Redis cache wrapper with JSON serialisation."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Low-level primitives
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        """Return the deserialised value for *key*, or ``None`` if absent."""
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("cache_get_failed", key=key, error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Serialise *value* to JSON and store under *key* with optional TTL."""
        effective_ttl = ttl if ttl is not None else settings.analytics_cache_ttl
        try:
            serialised = json.dumps(value, cls=_CustomEncoder)
            await self._redis.set(key, serialised, ex=effective_ttl)
        except Exception as exc:
            logger.warning("cache_set_failed", key=key, error=str(exc))

    async def exists(self, key: str) -> bool:
        """Return True if *key* exists in Redis (regardless of value)."""
        try:
            return bool(await self._redis.exists(key))
        except Exception as exc:
            logger.warning("cache_exists_failed", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> None:
        """Remove *key* from the cache."""
        try:
            await self._redis.delete(key)
        except Exception as exc:
            logger.warning("cache_delete_failed", key=key, error=str(exc))

    async def set_dedup_key(self, ticker: str, event_time: datetime) -> None:
        """Mark (ticker, event_time) as seen.  TTL matches analytics cache TTL."""
        key = f"dedup:{ticker}:{event_time.isoformat()}"
        # Short TTL — we only need dedup within a reasonable replay window
        await self.set(key, 1, ttl=3600)

    # ------------------------------------------------------------------
    # Higher-level helpers used by API routes
    # ------------------------------------------------------------------

    async def cache_response(
        self,
        cache_key: str,
        data: Any,
        ttl: int | None = None,
    ) -> None:
        """Convenience wrapper for caching API responses."""
        await self.set(cache_key, data, ttl=ttl)

    async def get_cached_response(self, cache_key: str) -> Any | None:
        """Return a previously cached API response or ``None``."""
        return await self.get(cache_key)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            return await self._redis.ping()
        except Exception:
            return False


async def create_redis_client() -> aioredis.Redis:
    """Create and return an async Redis client."""
    client: aioredis.Redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    return client
