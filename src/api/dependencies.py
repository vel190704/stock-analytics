"""FastAPI dependency injection providers.

All application-level singletons (DB session, Redis, repositories, services)
are wired here and injected into route handlers via ``Depends()``.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import AsyncSessionFactory
from src.database.repository import StockRepository
from src.services.alert_service import AlertService
from src.services.analytics_service import AnalyticsService
from src.services.cache_service import CacheService
from src.services.portfolio_service import PortfolioService


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Redis client — retrieved from application state (set during lifespan)
# ---------------------------------------------------------------------------


async def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


async def get_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StockRepository:
    return StockRepository(session)


# ---------------------------------------------------------------------------
# Cache service
# ---------------------------------------------------------------------------


async def get_cache(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> CacheService:
    return CacheService(redis)


async def get_alert_service(request: Request) -> AlertService:
    return request.app.state.alert_service


async def get_portfolio_service(request: Request) -> PortfolioService:
    return request.app.state.portfolio_service


# ---------------------------------------------------------------------------
# Analytics service
# ---------------------------------------------------------------------------


async def get_analytics_service(
    repo: Annotated[StockRepository, Depends(get_repository)],
    cache: Annotated[CacheService, Depends(get_cache)],
) -> AnalyticsService:
    return AnalyticsService(repository=repo, cache=cache)
