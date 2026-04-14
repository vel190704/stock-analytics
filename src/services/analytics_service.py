"""Analytics business-logic layer.

Sits between the API routes and the repository/cache layers.
All analytics queries are cached in Redis with a configurable TTL.
"""

from datetime import datetime, timezone
from typing import Any

from src.config.settings import settings
from src.database.repository import StockRepository
from src.services.cache_service import CacheService
from src.utils.logger import get_logger

logger = get_logger(__name__)

_TTL = settings.analytics_cache_ttl


class AnalyticsService:
    """Business logic for all analytics endpoints."""

    def __init__(self, repository: StockRepository, cache: CacheService) -> None:
        self._repo = repository
        self._cache = cache

    # ------------------------------------------------------------------
    # Market movers
    # ------------------------------------------------------------------

    async def get_top_gainers(self, limit: int = 10) -> list[dict[str, Any]]:
        cache_key = f"analytics:top_gainers:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_top_gainers(limit=limit)
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    async def get_top_losers(self, limit: int = 10) -> list[dict[str, Any]]:
        cache_key = f"analytics:top_losers:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_top_losers(limit=limit)
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    async def get_volume_leaders(self, limit: int = 10) -> list[dict[str, Any]]:
        cache_key = f"analytics:volume_leaders:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_volume_leaders(limit=limit)
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    # ------------------------------------------------------------------
    # Technical indicators
    # ------------------------------------------------------------------

    async def get_moving_average(
        self,
        ticker: str,
        window: int = 20,
    ) -> list[dict[str, Any]]:
        cache_key = f"analytics:ma:{ticker.upper()}:{window}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_moving_average(ticker=ticker, window=window)
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    async def get_volatility(
        self,
        ticker: str,
        sample_size: int = 100,
    ) -> dict[str, Any]:
        cache_key = f"analytics:volatility:{ticker.upper()}:{sample_size}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_volatility(ticker=ticker, limit=sample_size)
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    # ------------------------------------------------------------------
    # Ticker overview
    # ------------------------------------------------------------------

    async def get_all_tickers_latest(self) -> list[dict[str, Any]]:
        cache_key = "analytics:tickers:latest"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        events = await self._repo.get_latest_per_ticker()
        data = [
            {
                "ticker": e.ticker,
                "exchange": e.exchange,
                "close": e.close,
                "pct_change": e.pct_change,
                "volume": e.volume,
                "event_time": e.event_time.isoformat() if e.event_time else None,
            }
            for e in events
        ]
        await self._cache.set(cache_key, data, ttl=_TTL)
        return data

    async def get_ticker_stats(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any] | None:
        cache_key = f"analytics:stats:{ticker.upper()}:{start.date()}:{end.date()}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._repo.get_ticker_stats(ticker=ticker, start=start, end=end)
        if data:
            await self._cache.set(cache_key, data, ttl=_TTL)
        return data
