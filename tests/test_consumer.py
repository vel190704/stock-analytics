"""Unit tests for the consumer message processor."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.consumer.processor import MessageProcessor, StockMessage


class TestStockMessageSchema:
    def test_valid_message_parses(self, valid_message):
        msg = StockMessage.model_validate(valid_message)
        assert msg.ticker == "AAPL"
        assert msg.close > 0

    def test_ticker_is_normalised_to_uppercase(self):
        msg = StockMessage.model_validate(
            {
                "ticker": "aapl",
                "exchange": "NASDAQ",
                "event_time": "2025-06-01T10:00:00+00:00",
                "open": "10.0",
                "close": "10.5",
                "high": "11.0",
                "low": "9.5",
                "volume": 1000,
                "source": "test",
            }
        )
        assert msg.ticker == "AAPL"

    def test_zero_open_price_raises_validation_error(self):
        with pytest.raises(Exception):
            StockMessage.model_validate(
                {
                    "ticker": "AAPL",
                    "event_time": "2025-06-01T10:00:00+00:00",
                    "open": "0.0",
                    "close": "100.0",
                    "high": "101.0",
                    "low": "99.0",
                    "volume": 1000,
                }
            )

    def test_high_less_than_low_raises_validation_error(self):
        with pytest.raises(Exception):
            StockMessage.model_validate(
                {
                    "ticker": "AAPL",
                    "event_time": "2025-06-01T10:00:00+00:00",
                    "open": "100.0",
                    "close": "100.0",
                    "high": "98.0",   # high < low → invalid
                    "low": "99.0",
                    "volume": 1000,
                }
            )

    def test_naive_datetime_converted_to_utc(self):
        msg = StockMessage.model_validate(
            {
                "ticker": "AAPL",
                "event_time": "2025-06-01T10:00:00",
                "open": "10.0",
                "close": "10.5",
                "high": "11.0",
                "low": "9.5",
                "volume": 1000,
            }
        )
        assert msg.event_time.tzinfo is not None


class TestMessageProcessor:
    @pytest.fixture
    def processor(self, mock_repository, cache_service, mock_broadcaster, mock_dlq_producer):
        return MessageProcessor(
            repository=mock_repository,
            cache_service=cache_service,
            broadcaster=mock_broadcaster,
            dlq_producer=mock_dlq_producer,
        )

    @pytest.mark.asyncio
    async def test_valid_message_accepted(self, processor, valid_message):
        result = await processor.process(valid_message)
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_schema_sent_to_dlq(
        self, processor, mock_dlq_producer, invalid_message
    ):
        result = await processor.process(invalid_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_future_timestamp_rejected(
        self, processor, mock_dlq_producer
    ):
        far_future = "2099-01-01T00:00:00+00:00"
        msg = {
            "ticker": "AAPL",
            "event_time": far_future,
            "open": "100.0",
            "close": "100.5",
            "high": "101.0",
            "low": "99.0",
            "volume": 1000,
            "source": "test",
        }
        result = await processor.process(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_duplicate_message_skipped(
        self, processor, mock_repository, valid_message, mock_redis
    ):
        # First call — should succeed
        result1 = await processor.process(valid_message)
        assert result1 is True

        # Mark the dedup key as existing in Redis
        mock_redis.exists.return_value = 1

        # Second call — same (ticker, event_time) should be duplicate
        result2 = await processor.process(valid_message)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_flush_batch_calls_bulk_insert(
        self, processor, mock_repository, valid_message
    ):
        await processor.process(valid_message)
        await processor.flush_batch()
        mock_repository.bulk_insert.assert_called_once()

    @pytest.fixture
    def valid_message(self):
        return {
            "schema_version": "1.0",
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "event_time": "2025-01-01T10:00:00+00:00",
            "ingested_at": "2025-01-01T10:00:00.123456+00:00",
            "open": "180.00",
            "close": "182.50",
            "high": "183.10",
            "low": "179.75",
            "volume": 2150000,
            "vwap": "181.20",
            "source": "polygon",
        }

    @pytest.fixture
    def invalid_message(self):
        return {
            "ticker": "BAD",
            "event_time": "2025-01-01T10:00:00+00:00",
            "open": "-1.0",  # negative price → should fail validation
            "close": "0.0",
            "high": "0.0",
            "low": "0.0",
            "volume": 0,
        }
