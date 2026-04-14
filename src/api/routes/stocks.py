"""Stocks REST API routes.

Endpoints:
    GET  /stocks                     — all tickers, latest price
    GET  /stocks/{ticker}            — OHLCV history
    GET  /stocks/{ticker}/latest     — single latest event
    GET  /stocks/{ticker}/stats      — aggregated statistics
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_analytics_service, get_repository
from src.database.repository import StockRepository
from src.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TickerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    exchange: str | None
    close: Decimal
    pct_change: Decimal | None
    volume: int
    event_time: datetime


class OHLCVEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    exchange: str | None
    event_time: datetime
    ingested_at: datetime
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: int
    vwap: Decimal | None
    price_change: Decimal | None
    pct_change: Decimal | None
    source: str | None


class OHLCVResponse(BaseModel):
    ticker: str
    interval: str
    start: datetime
    end: datetime
    count: int
    data: list[OHLCVEvent]


class TickerStats(BaseModel):
    ticker: str
    start: datetime
    end: datetime
    min_close: Decimal | None
    max_close: Decimal | None
    avg_close: Decimal | None
    total_volume: int | None
    event_count: int


class PaginatedTickerList(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[TickerSummary]


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedTickerList)
async def list_tickers(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> PaginatedTickerList:
    """Return all tickers with their most recent price."""
    all_tickers = await svc.get_all_tickers_latest()
    total = len(all_tickers)
    start_idx = (page - 1) * page_size
    page_data = all_tickers[start_idx : start_idx + page_size]
    return PaginatedTickerList(
        total=total,
        page=page,
        page_size=page_size,
        data=[TickerSummary(**item) for item in page_data],
    )


@router.get("/{ticker}", response_model=OHLCVResponse)
async def get_ohlcv_history(
    ticker: str,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    repo: StockRepository = Depends(get_repository),
) -> OHLCVResponse:
    """Return OHLCV history for a ticker within the given time range."""
    now = datetime.now(timezone.utc)
    resolved_end = end or now
    resolved_start = start or datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    if resolved_start >= resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start must be before end",
        )

    events = await repo.get_ohlcv_history(
        ticker=ticker.upper(),
        start=resolved_start,
        end=resolved_end,
        limit=limit,
    )

    return OHLCVResponse(
        ticker=ticker.upper(),
        interval="raw",
        start=resolved_start,
        end=resolved_end,
        count=len(events),
        data=[OHLCVEvent.model_validate(e) for e in events],
    )


@router.get("/{ticker}/latest", response_model=OHLCVEvent)
async def get_latest_event(
    ticker: str,
    repo: StockRepository = Depends(get_repository),
) -> OHLCVEvent:
    """Return the single most-recent event for a ticker."""
    event = await repo.get_latest_for_ticker(ticker.upper())
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for ticker {ticker.upper()!r}",
        )
    return OHLCVEvent.model_validate(event)


@router.get("/{ticker}/stats", response_model=TickerStats)
async def get_ticker_stats(
    ticker: str,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    svc: AnalyticsService = Depends(get_analytics_service),
) -> TickerStats:
    """Return min/max/avg statistics for a ticker over a date range."""
    now = datetime.now(timezone.utc)
    resolved_end = end or now
    resolved_start = start or datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    stats = await svc.get_ticker_stats(
        ticker=ticker.upper(),
        start=resolved_start,
        end=resolved_end,
    )
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for ticker {ticker.upper()!r} in the given range",
        )
    return TickerStats(**stats)
