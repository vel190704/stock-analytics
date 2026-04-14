"""Confluent Kafka producer for stock price events.

Design decisions:
- Partition key = ticker symbol (consistent routing, keeps per-ticker order)
- Delivery callbacks detect and log failed publishes
- Graceful shutdown via producer.flush(timeout=30)
- Runs a polling loop on a background thread for delivery callbacks
"""

import asyncio
import json
import threading
from typing import Any

from confluent_kafka import KafkaException, Producer

from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.metrics import messages_produced_total

logger = get_logger(__name__)


class StockProducer:
    """Thin async wrapper around the confluent-kafka ``Producer``."""

    def __init__(self) -> None:
        kafka_conf: dict[str, Any] = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "compression.type": "snappy",
            "acks": "all",
            "retries": 5,
            "retry.backoff.ms": 300,
            "linger.ms": 5,         # micro-batching for throughput
            "batch.size": 65536,
            "enable.idempotence": True,
        }
        self._producer = Producer(kafka_conf)
        self._stop_poll = threading.Event()
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="kafka-producer-poll"
        )
        self._poll_thread.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Background thread: drains the delivery-callback queue."""
        while not self._stop_poll.is_set():
            self._producer.poll(timeout=0.5)

    def _delivery_callback(
        self,
        err: Exception | None,
        msg: Any,
    ) -> None:
        if err:
            logger.error(
                "kafka_delivery_failed",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                error=str(err),
            )
        else:
            ticker = msg.key().decode() if msg.key() else "unknown"
            messages_produced_total.labels(ticker=ticker).inc()
            logger.debug(
                "kafka_delivery_success",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                ticker=ticker,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def produce(
        self,
        message: dict[str, Any],
        topic: str | None = None,
    ) -> None:
        """Serialise *message* to JSON and enqueue it to Kafka.

        Uses the ticker as the partition key for consistent routing.
        """
        target_topic = topic or settings.kafka_topic
        ticker = message.get("ticker", "UNKNOWN")
        payload = json.dumps(message, default=str).encode()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._produce_sync,
            target_topic,
            ticker,
            payload,
        )

    def _produce_sync(self, topic: str, key: str, payload: bytes) -> None:
        try:
            self._producer.produce(
                topic=topic,
                key=key.encode(),
                value=payload,
                on_delivery=self._delivery_callback,
            )
        except KafkaException as exc:
            logger.error("kafka_produce_error", topic=topic, key=key, error=str(exc))
            raise

    async def produce_batch(
        self,
        messages: list[dict[str, Any]],
        topic: str | None = None,
    ) -> None:
        """Produce a list of messages, one per ticker event."""
        for message in messages:
            await self.produce(message, topic=topic)

    async def flush(self, timeout: float = 30.0) -> int:
        """Flush all queued messages synchronously."""
        loop = asyncio.get_event_loop()
        remaining: int = await loop.run_in_executor(
            None, self._producer.flush, timeout
        )
        if remaining:
            logger.warning("kafka_flush_incomplete", remaining_messages=remaining)
        return remaining

    async def close(self) -> None:
        """Flush pending messages and stop the polling thread."""
        await self.flush()
        self._stop_poll.set()
        self._poll_thread.join(timeout=5)
        logger.info("kafka_producer_closed")
