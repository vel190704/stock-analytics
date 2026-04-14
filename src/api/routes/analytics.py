"""Analytics REST API routes.

Endpoints:
    GET /analytics/top-gainers
    GET /analytics/top-losers
    GET /analytics/volume-leaders
    GET /analytics/moving-average/{ticker}
    GET /analytics/volatility/{ticker}
"""

from decimal import Decimal
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import get_analytics_service
from src.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MoverItem(BaseModel):
    ticker: str
    close: Decimal | None = None
    pct_change: Decimal | None = None
    event_time: datetime | None = None


class VolumeLeaderItem(BaseModel):
    ticker: str
    total_volume: int


class MovingAveragePoint(BaseModel):
    event_time: datetime
    close: Decimal
    moving_average: Decimal | None


class VolatilityResult(BaseModel):
    ticker: str
    volatility: Decimal | None
    sample_size: int


class PaginatedMovers(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[MoverItem]


class PaginatedVolumeLeaders(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[VolumeLeaderItem]


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/top-gainers", response_model=PaginatedMovers)
async def top_gainers(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> PaginatedMovers:
    """Top tickers by percentage gain today."""
    data = await svc.get_top_gainers(limit=page_size * page)
    total = len(data)
    start = (page - 1) * page_size
    page_data = data[start : start + page_size]
    return PaginatedMovers(
        total=total,
        page=page,
        page_size=page_size,
        data=[MoverItem(**row) for row in page_data],
    )


@router.get("/top-losers", response_model=PaginatedMovers)
async def top_losers(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> PaginatedMovers:
    """Bottom tickers by percentage change today."""
    data = await svc.get_top_losers(limit=page_size * page)
    total = len(data)
    start = (page - 1) * page_size
    page_data = data[start : start + page_size]
    return PaginatedMovers(
        total=total,
        page=page,
        page_size=page_size,
        data=[MoverItem(**row) for row in page_data],
    )


@router.get("/volume-leaders", response_model=PaginatedVolumeLeaders)
async def volume_leaders(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> PaginatedVolumeLeaders:
    """Tickers with highest traded volume today."""
    data = await svc.get_volume_leaders(limit=page_size * page)
    total = len(data)
    start = (page - 1) * page_size
    page_data = data[start : start + page_size]
    return PaginatedVolumeLeaders(
        total=total,
        page=page,
        page_size=page_size,
        data=[VolumeLeaderItem(**row) for row in page_data],
    )


@router.get("/moving-average/{ticker}", response_model=list[MovingAveragePoint])
async def moving_average(
    ticker: str,
    window: Annotated[int, Query(ge=2, le=200)] = 20,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> list[MovingAveragePoint]:
    """Simple moving average of close price over the last *window* data points."""
    data = await svc.get_moving_average(ticker=ticker.upper(), window=window)
    return [MovingAveragePoint(**row) for row in data]


@router.get("/volatility/{ticker}", response_model=VolatilityResult)
async def volatility(
    ticker: str,
    sample_size: Annotated[int, Query(ge=10, le=500)] = 100,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> VolatilityResult:
    """Rolling standard deviation of close prices as a volatility measure."""
    data = await svc.get_volatility(ticker=ticker.upper(), sample_size=sample_size)
    return VolatilityResult(**data)
