"""Data-source adapters.

Primary: Polygon.io REST API (requires POLYGON_API_KEY).
Fallback: yfinance (no API key required, rate-limited).

Both adapters return a list of ``StockMessage`` dicts that are then forwarded
to the Kafka producer.
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

import httpx
import pandas as pd
import yfinance as yf

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"


def _build_message(
    ticker: str,
    exchange: str,
    event_time: datetime,
    open_price: float,
    close_price: float,
    high: float,
    low: float,
    volume: int,
    vwap: float | None,
    source: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker.upper(),
        "exchange": exchange,
        "event_time": event_time.isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "open": round(open_price, 4),
        "close": round(close_price, 4),
        "high": round(high, 4),
        "low": round(low, 4),
        "volume": int(volume),
        "vwap": round(vwap, 4) if vwap else None,
        "source": source,
    }


class PolygonDataSource:
    """Fetches the latest aggregate (1-minute bar) for each ticker via Polygon REST."""

    BASE_URL = "https://api.polygon.io"

    def __init__(self) -> None:
        self._api_key = settings.polygon_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PolygonDataSource":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=10.0,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    async def fetch_latest(self, tickers: list[str]) -> list[dict[str, Any]]:
        """Return one message dict per ticker using the /v2/snapshot endpoint."""
        if not self._client:
            raise RuntimeError("Use as async context manager")

        ticker_csv = ",".join(t.upper() for t in tickers)
        try:
            resp = await self._client.get(
                f"/v2/snapshot/locale/us/markets/stocks/tickers",
                params={"tickers": ticker_csv},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("polygon_fetch_failed", error=str(exc))
            return []

        payload = resp.json()
        messages: list[dict[str, Any]] = []

        for snap in payload.get("tickers", []):
            day = snap.get("day", {})
            ticker = snap.get("ticker", "")
            if not ticker or not day:
                continue

            now = datetime.now(timezone.utc)
            msg = _build_message(
                ticker=ticker,
                exchange=snap.get("primaryExch", "US"),
                event_time=now,
                open_price=float(day.get("o", 0)),
                close_price=float(day.get("c", 0)),
                high=float(day.get("h", 0)),
                low=float(day.get("l", 0)),
                volume=int(day.get("v", 0)),
                vwap=float(day.get("vw", 0)) or None,
                source="polygon",
            )
            messages.append(msg)

        logger.debug("polygon_fetched", count=len(messages))
        return messages


class YFinanceDataSource:
    """Fallback data source using yfinance (synchronous, run in threadpool)."""

    async def fetch_latest(self, tickers: list[str]) -> list[dict[str, Any]]:
        """Download 1-day 1-minute bars and return the latest bar per ticker."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, tickers)

    def _fetch_sync(self, tickers: list[str]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for ticker in tickers:
            try:
                data = yf.download(
                    tickers=ticker,
                    period="1d",
                    interval="1m",
                    progress=False,
                    auto_adjust=True,
                )

                # yfinance can return MultiIndex columns depending on version/options.
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker in data.columns.get_level_values(-1):
                        data = data.xs(ticker, axis=1, level=-1, drop_level=True)
                    else:
                        data = data.droplevel(-1, axis=1)

                if data.empty:
                    continue
                row = data.iloc[-1]
                event_time = data.index[-1].to_pydatetime()
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)

                msg = _build_message(
                    ticker=ticker,
                    exchange="US",
                    event_time=event_time,
                    open_price=float(row["Open"]),
                    close_price=float(row["Close"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    volume=int(row["Volume"]),
                    vwap=None,
                    source="yfinance",
                )
                messages.append(msg)
            except Exception as exc:
                logger.warning("yfinance_fetch_failed", ticker=ticker, error=str(exc))
        logger.debug("yfinance_fetched", count=len(messages))
        return messages


class SimulatedDataSource:
    """Deterministic random-walk simulator for local development / tests.

    Generates realistic-looking OHLCV data without any external API call.
    """

    _prices: dict[str, float] = {}

    async def fetch_latest(self, tickers: list[str]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for ticker in tickers:
            if ticker not in self._prices:
                self._prices[ticker] = round(random.uniform(50.0, 500.0), 2)

            price = self._prices[ticker]
            close = round(price * (1 + random.uniform(-0.005, 0.005)), 4)
            self._prices[ticker] = close

            open_p = round(close * (1 + random.uniform(-0.002, 0.002)), 4)
            high = round(max(open_p, close) * (1 + random.uniform(0, 0.003)), 4)
            low = round(min(open_p, close) * (1 - random.uniform(0, 0.003)), 4)
            volume = random.randint(100_000, 5_000_000)
            vwap = round((high + low + close) / 3, 4)

            messages.append(
                _build_message(
                    ticker=ticker,
                    exchange="SIM",
                    event_time=now,
                    open_price=open_p,
                    close_price=close,
                    high=high,
                    low=low,
                    volume=volume,
                    vwap=vwap,
                    source="simulated",
                )
            )
        return messages


def get_data_source() -> PolygonDataSource | YFinanceDataSource | SimulatedDataSource:
    """Return the highest-priority available data source."""
    if settings.polygon_api_key:
        return PolygonDataSource()
    if settings.allow_simulated_data:
        logger.info("data_source_selected", source="simulated")
        return SimulatedDataSource()
    logger.info("data_source_selected", source="yfinance")
    return YFinanceDataSource()
