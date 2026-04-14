from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import StockEvent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StockRepository:
    """Data-access layer for ``stock_events``.

    All methods accept an ``AsyncSession`` so that the caller controls the
    transaction boundary (typical FastAPI dependency-injection pattern).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def bulk_insert(self, events: list[dict[str, Any]]) -> int:
        """Insert a batch of stock events, ignoring duplicate (ticker, event_time) pairs.

        Returns the number of rows actually inserted.
        """
        if not events:
            return 0

        stmt = (
            insert(StockEvent)
            .values(events)
            .on_conflict_do_nothing()
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        await self._session.commit()
        inserted = result.rowcount or 0
        logger.debug("bulk_insert_complete", inserted=inserted, attempted=len(events))
        return inserted

    # ------------------------------------------------------------------
    # Reads — latest prices
    # ------------------------------------------------------------------

    async def get_latest_per_ticker(self) -> list[StockEvent]:
        """Return the most recent event for every ticker in the database."""
        subq = (
            select(
                StockEvent.ticker,
                func.max(StockEvent.event_time).label("max_time"),
            )
            .group_by(StockEvent.ticker)
            .subquery()
        )
        stmt = select(StockEvent).join(
            subq,
            (StockEvent.ticker == subq.c.ticker)
            & (StockEvent.event_time == subq.c.max_time),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_for_ticker(self, ticker: str) -> StockEvent | None:
        """Return the single most-recent event for *ticker*."""
        stmt = (
            select(StockEvent)
            .where(StockEvent.ticker == ticker.upper())
            .order_by(StockEvent.event_time.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Reads — OHLCV history
    # ------------------------------------------------------------------

    async def get_ohlcv_history(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[StockEvent]:
        """Return raw OHLCV rows for *ticker* between *start* and *end*."""
        stmt = (
            select(StockEvent)
            .where(
                StockEvent.ticker == ticker.upper(),
                StockEvent.event_time >= start,
                StockEvent.event_time <= end,
            )
            .order_by(StockEvent.event_time.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Reads — aggregated stats
    # ------------------------------------------------------------------

    async def get_ticker_stats(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any] | None:
        """Return min/max/avg close and total volume for *ticker* in range."""
        stmt = select(
            func.min(StockEvent.close).label("min_close"),
            func.max(StockEvent.close).label("max_close"),
            func.avg(StockEvent.close).label("avg_close"),
            func.sum(StockEvent.volume).label("total_volume"),
            func.count(StockEvent.id).label("event_count"),
        ).where(
            StockEvent.ticker == ticker.upper(),
            StockEvent.event_time >= start,
            StockEvent.event_time <= end,
        )
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None or row.event_count == 0:
            return None
        return {
            "ticker": ticker.upper(),
            "start": start,
            "end": end,
            "min_close": row.min_close,
            "max_close": row.max_close,
            "avg_close": row.avg_close,
            "total_volume": row.total_volume,
            "event_count": row.event_count,
        }

    # ------------------------------------------------------------------
    # Reads — analytics
    # ------------------------------------------------------------------

    async def get_top_gainers(self, limit: int = 10) -> list[dict[str, Any]]:
        """Top *limit* tickers by pct_change for today."""
        stmt = text(
            """
            SELECT DISTINCT ON (ticker)
                ticker, close, pct_change, volume, event_time
            FROM stock_events
            WHERE pct_change IS NOT NULL
            ORDER BY ticker, event_time DESC
            """
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        sorted_rows = sorted(rows, key=lambda r: r["pct_change"], reverse=True)
        return [dict(r) for r in sorted_rows[:limit]]

    async def get_top_losers(self, limit: int = 10) -> list[dict[str, Any]]:
        """Bottom *limit* tickers by pct_change for today."""
        stmt = text(
            """
            SELECT DISTINCT ON (ticker)
                ticker, close, pct_change, volume, event_time
            FROM stock_events
            WHERE pct_change IS NOT NULL
            ORDER BY ticker, event_time DESC
            """
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        sorted_rows = sorted(rows, key=lambda r: r["pct_change"])
        return [dict(r) for r in sorted_rows[:limit]]

    async def get_volume_leaders(self, limit: int = 10) -> list[dict[str, Any]]:
        """Top *limit* tickers by total volume today."""
        recent_stmt = text(
            """
            SELECT ticker, SUM(volume) AS total_volume
            FROM stock_events
            WHERE event_time >= NOW() - INTERVAL '24 hours'
            GROUP BY ticker
            ORDER BY total_volume DESC
            LIMIT :limit
            """
        )
        rows = (await self._session.execute(recent_stmt, {"limit": limit})).mappings().all()
        if rows:
            return [dict(r) for r in rows]

        fallback_stmt = text(
            """
            SELECT ticker, SUM(volume) AS total_volume
            FROM stock_events
            GROUP BY ticker
            ORDER BY total_volume DESC
            LIMIT :limit
            """
        )
        fallback_rows = (await self._session.execute(fallback_stmt, {"limit": limit})).mappings().all()
        return [dict(r) for r in fallback_rows]

    async def get_moving_average(
        self,
        ticker: str,
        window: int = 20,
    ) -> list[dict[str, Any]]:
        """Rolling simple moving average of *close* over *window* rows."""
        stmt = text(
            """
            SELECT
                event_time,
                close,
                AVG(close) OVER (
                    ORDER BY event_time
                    ROWS BETWEEN :window PRECEDING AND CURRENT ROW
                ) AS moving_average
            FROM stock_events
            WHERE ticker = :ticker
            ORDER BY event_time DESC
            LIMIT :window
            """
        )
        rows = (
            await self._session.execute(
                stmt, {"ticker": ticker.upper(), "window": window}
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def get_volatility(
        self,
        ticker: str,
        limit: int = 100,
    ) -> dict[str, Decimal | None]:
        """Rolling standard deviation of *close* prices."""
        stmt = text(
            """
            SELECT STDDEV(close) AS volatility, COUNT(*) AS sample_size
            FROM (
                SELECT close
                FROM stock_events
                WHERE ticker = :ticker
                ORDER BY event_time DESC
                LIMIT :limit
            ) sub
            """
        )
        row = (
            await self._session.execute(stmt, {"ticker": ticker.upper(), "limit": limit})
        ).one_or_none()
        if row is None:
            return {"ticker": ticker.upper(), "volatility": None, "sample_size": 0}
        return {
            "ticker": ticker.upper(),
            "volatility": row.volatility,
            "sample_size": row.sample_size,
        }

    async def ticker_exists(self, ticker: str) -> bool:
        """Return True if *ticker* has at least one event in the database."""
        stmt = (
            select(StockEvent.ticker)
            .where(StockEvent.ticker == ticker.upper())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
