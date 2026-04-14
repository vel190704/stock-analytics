"""Unit tests for the Kafka producer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch

import pytest

from src.producer.stock_producer import StockProducer


@pytest.fixture
def mock_confluent_producer():
    with patch("src.producer.stock_producer.Producer") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def producer(mock_confluent_producer):
    with patch("threading.Thread"):
        p = StockProducer()
        p._producer = mock_confluent_producer
        return p


class TestStockProducer:
    def test_produce_calls_underlying_producer(self, producer, mock_confluent_producer, valid_message):
        import asyncio

        asyncio.get_event_loop().run_until_complete(producer.produce(valid_message))

        mock_confluent_producer.produce.assert_called_once()
        call_args = mock_confluent_producer.produce.call_args
        assert call_args.kwargs["topic"] == "stock_prices" or call_args.args

    def test_message_serialised_as_json(self, producer, mock_confluent_producer, valid_message):
        import asyncio

        asyncio.get_event_loop().run_until_complete(producer.produce(valid_message))

        call_kwargs = mock_confluent_producer.produce.call_args.kwargs
        payload = call_kwargs.get("value") or mock_confluent_producer.produce.call_args.args[1]
        # Payload should be valid JSON bytes
        decoded = json.loads(payload.decode())
        assert decoded["ticker"] == "AAPL"

    def test_partition_key_is_ticker(self, producer, mock_confluent_producer, valid_message):
        import asyncio

        asyncio.get_event_loop().run_until_complete(producer.produce(valid_message))

        call_kwargs = mock_confluent_producer.produce.call_args.kwargs
        key = call_kwargs.get("key")
        assert key == b"AAPL"

    def test_produce_batch_calls_produce_multiple_times(self, producer, mock_confluent_producer):
        import asyncio

        messages = [
            {
                "schema_version": "1.0",
                "ticker": t,
                "exchange": "US",
                "event_time": "2025-06-01T10:00:00+00:00",
                "open": "100.0",
                "close": "101.0",
                "high": "102.0",
                "low": "99.0",
                "volume": 1000,
                "vwap": None,
                "source": "test",
            }
            for t in ["AAPL", "MSFT", "GOOGL"]
        ]
        asyncio.get_event_loop().run_until_complete(producer.produce_batch(messages))
        assert mock_confluent_producer.produce.call_count == 3

    @pytest.fixture
    def valid_message(self):
        return {
            "schema_version": "1.0",
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "event_time": "2025-06-01T10:00:00+00:00",
            "open": "180.00",
            "close": "182.50",
            "high": "183.10",
            "low": "179.75",
            "volume": 2150000,
            "vwap": "181.20",
            "source": "polygon",
        }
