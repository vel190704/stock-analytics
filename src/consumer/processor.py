"""Message processing pipeline.

Each incoming Kafka message passes through these stages in order:

1. Schema Validation   — Pydantic model; invalid → DLQ
2. Deduplication       — Redis (ticker, event_time) key; duplicate → skip
3. Timestamp Normalisation — UTC enforcement; future timestamps → DLQ
4. Enrichment          — add ingested_at, source metadata
5. Business Rules      — reject zero/negative prices, negative volume → DLQ
6. Async DB Write      — batched, flushed every 500 ms or 100 records
7. WebSocket Broadcast — push validated event to connected clients
8. Metrics Update      — Prometheus counters
"""

import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.utils.logger import get_logger
from src.utils.metrics import (
    messages_consumed_total,
    messages_dlq_total,
    processing_duration_seconds,
)

if TYPE_CHECKING:
    from src.services.alert_service import AlertService
    from src.api.websocket import WebSocketBroadcaster
    from src.database.repository import StockRepository
    from src.services.cache_service import CacheService

logger = get_logger(__name__)

# Maximum number of seconds a timestamp can be ahead of server time
_MAX_FUTURE_SECONDS = 5.0

# Flush batch every N records or after this many seconds
_BATCH_SIZE = 100
_BATCH_FLUSH_INTERVAL = 0.5  # seconds


class StockMessage(BaseModel):
    """Pydantic schema matching the Avro-compatible Kafka message format."""

    schema_version: str = "1.0"
    ticker: str = Field(..., min_length=1, max_length=10)
    exchange: str | None = None
    event_time: datetime
    ingested_at: datetime | None = None
    open: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    vwap: Decimal | None = None
    source: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("event_time", "ingested_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: object) -> object:
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> "StockMessage":
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) < low ({self.low})")
        if self.high < self.close or self.high < self.open:
            raise ValueError("high must be >= open and close")
        if self.low > self.close or self.low > self.open:
            raise ValueError("low must be <= open and close")
        return self


class MessageProcessor:
    """Stateful processor that buffers validated events and writes them in batches."""

    def __init__(
        self,
        repository: "StockRepository",
        cache_service: "CacheService",
        broadcaster: "WebSocketBroadcaster",
        dlq_producer: Any,  # StockProducer
        alert_service: "AlertService | None" = None,
    ) -> None:
        self._repo = repository
        self._cache = cache_service
        self._broadcaster = broadcaster
        self._dlq_producer = dlq_producer
        self._alert_service = alert_service

        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._flush_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process(self, raw: dict[str, Any]) -> bool:
        """Run the full pipeline for one raw Kafka message dict.

        Returns ``True`` if the message was accepted, ``False`` otherwise.
        """
        ticker = raw.get("ticker", "UNKNOWN")

        # Stage 1 — Schema Validation
        with processing_duration_seconds.labels(stage="validation").time():
            message = await self._validate(raw)
        if message is None:
            return False

        # Stage 2 — Deduplication
        with processing_duration_seconds.labels(stage="deduplication").time():
            is_duplicate = await self._is_duplicate(message)
        if is_duplicate:
            messages_consumed_total.labels(ticker=ticker, status="duplicate").inc()
            logger.debug("message_duplicate_skipped", ticker=ticker)
            return False

        # Stage 3 — Timestamp Normalisation (already done in Pydantic validator)
        if not await self._validate_timestamp(message):
            return False

        # Stage 4 — Enrichment
        message = self._enrich(message)

        # Stage 5 — Business Rules
        if not await self._apply_business_rules(message):
            return False

        # Stage 6 — Buffer for DB write
        event_dict = self._to_db_dict(message)
        self._batch.append(event_dict)

        # Cache latest price snapshot for low-latency portfolio reads
        await self._cache.set(
            f"latest:{message.ticker}",
            {
                "ticker": message.ticker,
                "close": message.close,
                "price_change": float(message.close - message.open),
                "pct_change": float(((message.close - message.open) / message.open) * 100)
                if message.open
                else 0.0,
                "volume": message.volume,
                "event_time": message.event_time,
            },
            ttl=30,
        )

        if self._alert_service is not None:
            asyncio.create_task(self._alert_service.process_stock_event(message.model_dump(mode="json")))

        # Stage 7 — WebSocket Broadcast (fire-and-forget)
        asyncio.create_task(self._broadcaster.broadcast(message.model_dump(mode="json")))

        # Stage 8 — Metrics
        messages_consumed_total.labels(ticker=ticker, status="success").inc()

        # Flush batch if thresholds are met
        await self._maybe_flush()
        return True

    async def flush_batch(self) -> None:
        """Force-flush the current buffer to the database."""
        async with self._flush_lock:
            if not self._batch:
                return
            batch = self._batch[:]
            self._batch.clear()
            self._last_flush = time.monotonic()

        from src.utils.metrics import db_write_duration_seconds

        with db_write_duration_seconds.time():
            inserted = await self._repo.bulk_insert(batch)

        logger.info("batch_flushed", attempted=len(batch), inserted=inserted)

    # ------------------------------------------------------------------
    # Private pipeline stages
    # ------------------------------------------------------------------

    async def _validate(self, raw: dict[str, Any]) -> StockMessage | None:
        try:
            return StockMessage.model_validate(raw)
        except Exception as exc:
            ticker = raw.get("ticker", "UNKNOWN")
            logger.warning("schema_validation_failed", ticker=ticker, error=str(exc))
            await self._send_to_dlq(raw, reason="schema_validation_failed")
            messages_dlq_total.labels(ticker=ticker, reason="schema_validation").inc()
            return None

    async def _is_duplicate(self, msg: StockMessage) -> bool:
        key = f"dedup:{msg.ticker}:{msg.event_time.isoformat()}"
        return await self._cache.exists(key)

    async def _validate_timestamp(self, msg: StockMessage) -> bool:
        now = datetime.now(timezone.utc)
        delta = (msg.event_time - now).total_seconds()
        if delta > _MAX_FUTURE_SECONDS:
            logger.warning(
                "future_timestamp_rejected",
                ticker=msg.ticker,
                event_time=msg.event_time.isoformat(),
                delta_seconds=delta,
            )
            await self._send_to_dlq(msg.model_dump(mode="json"), reason="future_timestamp")
            messages_dlq_total.labels(ticker=msg.ticker, reason="future_timestamp").inc()
            return False
        return True

    def _enrich(self, msg: StockMessage) -> StockMessage:
        if msg.ingested_at is None:
            return msg.model_copy(
                update={"ingested_at": datetime.now(timezone.utc)}
            )
        return msg

    async def _apply_business_rules(self, msg: StockMessage) -> bool:
        if any(v <= 0 for v in (msg.open, msg.close, msg.high, msg.low)):
            logger.warning("business_rule_failed", ticker=msg.ticker, rule="zero_or_negative_price")
            await self._send_to_dlq(msg.model_dump(mode="json"), reason="zero_or_negative_price")
            messages_dlq_total.labels(ticker=msg.ticker, reason="invalid_price").inc()
            return False
        if msg.volume < 0:
            logger.warning("business_rule_failed", ticker=msg.ticker, rule="negative_volume")
            await self._send_to_dlq(msg.model_dump(mode="json"), reason="negative_volume")
            messages_dlq_total.labels(ticker=msg.ticker, reason="invalid_volume").inc()
            return False
        return True

    def _to_db_dict(self, msg: StockMessage) -> dict[str, Any]:
        return {
            "ticker": msg.ticker,
            "exchange": msg.exchange,
            "event_time": msg.event_time,
            "ingested_at": msg.ingested_at or datetime.now(timezone.utc),
            "open": msg.open,
            "close": msg.close,
            "high": msg.high,
            "low": msg.low,
            "volume": msg.volume,
            "vwap": msg.vwap,
            "source": msg.source,
        }

    async def _send_to_dlq(self, raw: dict[str, Any], reason: str) -> None:
        dlq_message = {**raw, "dlq_reason": reason, "dlq_at": datetime.now(timezone.utc).isoformat()}
        try:
            await self._dlq_producer.produce(
                dlq_message, topic=self._dlq_producer._topic if hasattr(self._dlq_producer, "_topic") else None
            )
        except Exception as exc:
            logger.error("dlq_produce_failed", reason=reason, error=str(exc))

    async def _maybe_flush(self) -> None:
        elapsed = time.monotonic() - self._last_flush
        if len(self._batch) >= _BATCH_SIZE or elapsed >= _BATCH_FLUSH_INTERVAL:
            await self.flush_batch()
