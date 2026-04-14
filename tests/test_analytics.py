"""Unit tests for analytics business logic."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.services.analytics_service import AnalyticsService


@pytest.fixture
def analytics_service(mock_repository, cache_service):
    return AnalyticsService(repository=mock_repository, cache=cache_service)


class TestAnalyticsService:
    @pytest.mark.asyncio
    async def test_get_top_gainers_returns_data(
        self, analytics_service, mock_repository
    ):
        mock_repository.get_top_gainers.return_value = [
            {"ticker": "NVDA", "close": Decimal("900.0"), "pct_change": Decimal("5.2")},
            {"ticker": "TSLA", "close": Decimal("250.0"), "pct_change": Decimal("3.1")},
        ]
        result = await analytics_service.get_top_gainers(limit=10)
        assert len(result) == 2
        assert result[0]["ticker"] == "NVDA"

    @pytest.mark.asyncio
    async def test_get_top_gainers_uses_cache(
        self, analytics_service, mock_repository, mock_redis
    ):
        cached_data = [{"ticker": "AAPL", "pct_change": "2.5"}]
        mock_redis.get.return_value = '{"data": "cached"}'

        # Should call cache.get() but the mock returns JSON for the key
        # Patch cache.get to return cached data directly
        analytics_service._cache.get = AsyncMock(return_value=cached_data)
        result = await analytics_service.get_top_gainers()

        assert result == cached_data
        mock_repository.get_top_gainers.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_top_losers_returns_data(
        self, analytics_service, mock_repository
    ):
        mock_repository.get_top_losers.return_value = [
            {"ticker": "META", "close": Decimal("400.0"), "pct_change": Decimal("-3.2")},
        ]
        result = await analytics_service.get_top_losers(limit=5)
        assert len(result) == 1
        assert result[0]["pct_change"] < 0

    @pytest.mark.asyncio
    async def test_get_moving_average_empty_result(
        self, analytics_service, mock_repository
    ):
        mock_repository.get_moving_average.return_value = []
        result = await analytics_service.get_moving_average("AAPL", window=20)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_volatility_returns_dict(
        self, analytics_service, mock_repository
    ):
        mock_repository.get_volatility.return_value = {
            "ticker": "AAPL",
            "volatility": Decimal("1.234"),
            "sample_size": 100,
        }
        result = await analytics_service.get_volatility("AAPL", sample_size=100)
        assert result["ticker"] == "AAPL"
        assert result["sample_size"] == 100

    @pytest.mark.asyncio
    async def test_get_volume_leaders_returns_sorted_data(
        self, analytics_service, mock_repository
    ):
        mock_repository.get_volume_leaders.return_value = [
            {"ticker": "AAPL", "total_volume": 10_000_000},
            {"ticker": "MSFT", "total_volume": 8_000_000},
        ]
        result = await analytics_service.get_volume_leaders(limit=10)
        assert result[0]["total_volume"] > result[1]["total_volume"]
