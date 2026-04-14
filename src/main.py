"""FastAPI application entry point.

Lifecycle:
  startup  → connect Redis, start Kafka producer + consumer
  shutdown → stop consumer, flush producer, close Redis + DB pool
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_cache, get_repository
from src.api.routes import analytics as analytics_router
from src.api.routes import alerts as alerts_router
from src.api.routes import backtest as backtest_router
from src.api.routes import portfolio as portfolio_router
from src.api.routes import sentiment as sentiment_router
from src.api.routes import stocks as stocks_router
from src.api.auth import router as auth_router
from src.api.middleware import setup_rate_limiting
from src.api.websocket import WebSocketBroadcaster, websocket_endpoint
from src.config.settings import settings
from src.consumer.processor import MessageProcessor
from src.consumer.stock_consumer import StockConsumer
from src.database.db import dispose_engine
from src.database.models import SentimentScore
from src.producer.data_source import get_data_source
from src.producer.stock_producer import StockProducer
from src.services.alert_service import AlertService
from src.services.cache_service import CacheService, create_redis_client
from src.services.portfolio_service import PortfolioService
from src.services.sentiment_service import fetch_and_score_sentiment
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def _refresh_sentiment_job() -> None:
    from src.database.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        assert isinstance(session, AsyncSession)
        for ticker in settings.tickers:
            try:
                scored = await fetch_and_score_sentiment(ticker)
                for item in scored:
                    session.add(
                        SentimentScore(
                            ticker=ticker,
                            headline=item.headline,
                            score=item.score,
                            label=item.label,
                            reason=item.reason,
                            source_url=item.source_url,
                        )
                    )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.warning("sentiment_refresh_failed", ticker=ticker, error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application-level resources across startup and shutdown."""
    logger.info("application_starting", environment=settings.environment)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    # Redis
    redis_client = await create_redis_client()
    app.state.redis = redis_client
    cache_service = CacheService(redis_client)
    alert_service = AlertService(redis_client)
    app.state.alert_service = alert_service
    app.state.portfolio_service = PortfolioService(redis_client)

    # WebSocket broadcaster (singleton shared by processor and route)
    broadcaster = WebSocketBroadcaster()
    app.state.broadcaster = broadcaster

    # Kafka producer
    producer = StockProducer()
    app.state.producer = producer

    # We need a db session for the processor; use a dedicated factory session
    # that is re-created per flush cycle — the consumer loop handles this
    # by keeping its own repository reference obtained from a long-lived session.
    from src.database.db import AsyncSessionFactory
    from src.database.repository import StockRepository

    db_session = AsyncSessionFactory()
    repository = StockRepository(db_session)

    # Message processor (stateful buffer)
    processor = MessageProcessor(
        repository=repository,
        cache_service=cache_service,
        broadcaster=broadcaster,
        dlq_producer=producer,
        alert_service=alert_service,
    )
    app.state.processor = processor

    # Kafka consumer
    consumer = StockConsumer(processor=processor)
    app.state.consumer = consumer
    consumer_task = asyncio.create_task(consumer.start(), name="kafka-consumer")

    # Ingestion loop — fetch from data source and produce to Kafka
    data_source = get_data_source()
    ingestion_task = asyncio.create_task(
        _ingestion_loop(producer, data_source),
        name="ingestion-loop",
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_refresh_sentiment_job, "interval", minutes=30, id="sentiment-refresh")
    scheduler.start()
    app.state.scheduler = scheduler

    logger.info("application_started")
    yield

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("application_shutting_down")

    ingestion_task.cancel()
    await asyncio.gather(ingestion_task, return_exceptions=True)

    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)

    await consumer.stop()
    consumer_task.cancel()
    await asyncio.gather(consumer_task, return_exceptions=True)

    await processor.flush_batch()

    await producer.close()
    await db_session.close()
    await redis_client.aclose()
    await dispose_engine()

    logger.info("application_stopped")


async def _ingestion_loop(producer: StockProducer, data_source: object) -> None:
    """Periodically fetch data and publish to Kafka."""
    while True:
        try:
            if hasattr(data_source, "__aenter__"):
                async with data_source as ds:  # type: ignore[attr-defined]
                    messages = await ds.fetch_latest(settings.tickers)
            else:
                messages = await data_source.fetch_latest(settings.tickers)  # type: ignore[union-attr]

            if messages:
                await producer.produce_batch(messages)
                logger.debug("ingestion_batch_produced", count=len(messages))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("ingestion_loop_error", error=str(exc))

        await asyncio.sleep(settings.poll_interval_seconds)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    application = FastAPI(
        title="Stock Analytics API",
        description="Real-time stock market analytics with AI-powered alerts and sentiment analysis",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "stocks", "description": "OHLCV data and analytics"},
            {"name": "analytics", "description": "Top gainers, losers, volume"},
            {"name": "alerts", "description": "AI-powered price alerts"},
            {"name": "portfolio", "description": "Portfolio tracking and P&L"},
            {"name": "sentiment", "description": "Claude AI sentiment scoring"},
            {"name": "backtest", "description": "Strategy backtesting engine"},
            {"name": "system", "description": "Health checks and metrics"},
        ],
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-ID middleware
    @application.middleware("http")
    async def add_request_id(request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-ID"] = request_id
        return response

    # Routers
    application.include_router(auth_router)
    application.include_router(stocks_router.router)
    application.include_router(analytics_router.router)
    application.include_router(alerts_router.router)
    application.include_router(portfolio_router.router)
    application.include_router(sentiment_router.router)
    application.include_router(backtest_router.router)

    setup_rate_limiting(application)

    @application.get("/", tags=["system"])
    async def api_root() -> dict[str, str]:
        return {
            "name": "Stock Analytics API",
            "version": "2.0.0",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }

    # Health check
    @application.get("/health", tags=["system"])
    async def health_check(request: Request) -> dict:
        checks: dict = {}

        # Redis
        try:
            checks["redis"] = await request.app.state.redis.ping()
        except Exception:
            checks["redis"] = False

        # DB
        try:
            from sqlalchemy import text
            from src.database.db import AsyncSessionFactory

            async with AsyncSessionFactory() as s:
                await s.execute(text("SELECT 1"))
            checks["postgres"] = True
        except Exception:
            checks["postgres"] = False

        # Kafka (producer present)
        checks["kafka"] = request.app.state.producer is not None

        all_ok = all(checks.values())
        return {
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
        }

    # Prometheus metrics
    @application.get("/metrics", tags=["system"], include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # WebSocket
    @application.websocket("/ws/stocks")
    async def ws_stocks(websocket: WebSocket) -> None:
        broadcaster: WebSocketBroadcaster = websocket.app.state.broadcaster
        await websocket_endpoint(websocket, broadcaster)

    @application.websocket("/ws/stocks/{ticker}")
    async def ws_stocks_ticker(websocket: WebSocket, ticker: str) -> None:
        broadcaster: WebSocketBroadcaster = websocket.app.state.broadcaster
        await websocket_endpoint(websocket, broadcaster, ticker=ticker)

    return application


app = create_app()
