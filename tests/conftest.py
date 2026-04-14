"""Shared pytest fixtures.

Spins up real PostgreSQL (TimescaleDB) and Kafka containers using
testcontainers for integration tests.  Unit tests use lightweight mocks only.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Async event loop (session-scoped for testcontainers)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# PostgreSQL container (integration tests only)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():
    """Start a TimescaleDB-compatible PostgreSQL container for integration tests."""
    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer(
            image="timescale/timescaledb:latest-pg15",
            username="test",
            password="test",
            dbname="testdb",
        )
        container.start()

        # Patch settings database URL to point to the test container
        dsn = container.get_connection_url().replace("psycopg2", "asyncpg")
        os.environ["DATABASE_URL"] = dsn

        yield container
        container.stop()
    except Exception:
        pytest.skip("testcontainers not available — skipping integration tests")


@pytest.fixture(scope="session")
def kafka_container():
    """Start a Kafka container for integration tests."""
    try:
        from testcontainers.kafka import KafkaContainer

        container = KafkaContainer(image="confluentinc/cp-kafka:7.6.0")
        container.start()

        bootstrap = container.get_bootstrap_server()
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap

        yield container
        container.stop()
    except Exception:
        pytest.skip("testcontainers not available — skipping integration tests")


# ---------------------------------------------------------------------------
# Async DB session (uses container if available, otherwise skips)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_container) -> AsyncGenerator:
    from src.database.db import AsyncSessionFactory, engine
    from src.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionFactory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Redis mock (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis() -> MagicMock:
    redis = AsyncMock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.set.return_value = True
    redis.exists.return_value = 0
    redis.delete.return_value = 1
    return redis


# ---------------------------------------------------------------------------
# Cache service (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_service(mock_redis) -> object:
    from src.services.cache_service import CacheService

    return CacheService(redis_client=mock_redis)


# ---------------------------------------------------------------------------
# Repository mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = AsyncMock()
    repo.bulk_insert.return_value = 1
    repo.get_latest_per_ticker.return_value = []
    repo.get_latest_for_ticker.return_value = None
    repo.get_top_gainers.return_value = []
    repo.get_top_losers.return_value = []
    repo.get_volume_leaders.return_value = []
    repo.get_moving_average.return_value = []
    repo.get_volatility.return_value = {"ticker": "AAPL", "volatility": None, "sample_size": 0}
    return repo


# ---------------------------------------------------------------------------
# WebSocket broadcaster mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_broadcaster() -> MagicMock:
    broadcaster = AsyncMock()
    broadcaster.broadcast.return_value = None
    return broadcaster


# ---------------------------------------------------------------------------
# DLQ producer mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_dlq_producer() -> MagicMock:
    producer = AsyncMock()
    producer.produce.return_value = None
    return producer


# ---------------------------------------------------------------------------
# Sample valid Kafka message
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_message() -> dict:
    return {
        "schema_version": "1.0",
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "event_time": "2025-06-01T10:00:00+00:00",
        "ingested_at": "2025-06-01T10:00:00.123456+00:00",
        "open": "180.00",
        "close": "182.50",
        "high": "183.10",
        "low": "179.75",
        "volume": 2150000,
        "vwap": "181.20",
        "source": "polygon",
    }


@pytest.fixture
def invalid_message() -> dict:
    """Message with zero close price — should be routed to DLQ."""
    return {
        "schema_version": "1.0",
        "ticker": "MSFT",
        "exchange": "NASDAQ",
        "event_time": "2025-06-01T10:00:00+00:00",
        "open": "0.00",
        "close": "0.00",
        "high": "0.00",
        "low": "0.00",
        "volume": 0,
        "source": "test",
    }
