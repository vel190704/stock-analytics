"""Async Confluent Kafka consumer.

Design decisions:
- Consumer group: ``stock-processor-group`` (configured via settings)
- Manual offset commits — only after successful processing + DB write
- Exponential backoff on reconnection failures (max 60 s)
- Runs on a dedicated asyncio task; graceful shutdown via ``stop()``
"""

import asyncio
import json
import time
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition

from src.config.settings import settings
from src.consumer.processor import MessageProcessor
from src.utils.logger import get_logger
from src.utils.metrics import kafka_consumer_lag

logger = get_logger(__name__)

_POLL_TIMEOUT = 1.0          # seconds — how long poll() blocks waiting for a message
_MAX_BACKOFF = 60.0          # seconds — maximum reconnection back-off delay
_INITIAL_BACKOFF = 1.0       # seconds — starting back-off


class StockConsumer:
    """Async wrapper around the confluent-kafka ``Consumer``."""

    def __init__(self, processor: MessageProcessor) -> None:
        self._processor = processor
        self._consumer: Consumer | None = None
        self._running = False
        self._backoff = _INITIAL_BACKOFF

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _build_consumer(self) -> Consumer:
        conf: dict[str, Any] = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,     # manual commits only
            "max.poll.interval.ms": 300_000,
            "session.timeout.ms": 45_000,
            "heartbeat.interval.ms": 3_000,
            "fetch.min.bytes": 1,
            "fetch.wait.max.ms": 500,
            "on_commit": self._on_commit_callback,
        }
        consumer = Consumer(conf)
        consumer.subscribe(
            [settings.kafka_topic],
            on_assign=self._on_assign,
            on_revoke=self._on_revoke,
        )
        return consumer

    def _on_assign(self, consumer: Consumer, partitions: list[TopicPartition]) -> None:
        logger.info("partitions_assigned", partitions=[p.partition for p in partitions])

    def _on_revoke(self, consumer: Consumer, partitions: list[TopicPartition]) -> None:
        logger.info("partitions_revoked", partitions=[p.partition for p in partitions])
        # Flush any buffered batch before rebalance
        asyncio.get_event_loop().create_task(self._processor.flush_batch())

    def _on_commit_callback(
        self, err: Exception | None, partitions: list[TopicPartition]
    ) -> None:
        if err:
            logger.error("offset_commit_failed", error=str(err))
        else:
            for p in partitions:
                logger.debug(
                    "offset_committed",
                    partition=p.partition,
                    offset=p.offset,
                )

    # ------------------------------------------------------------------
    # Main consume loop
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch the consume loop as a long-running coroutine."""
        self._running = True
        logger.info("consumer_starting", topic=settings.kafka_topic)

        while self._running:
            try:
                self._consumer = self._build_consumer()
                self._backoff = _INITIAL_BACKOFF
                await self._consume_loop()
            except KafkaException as exc:
                if not self._running:
                    break
                logger.error(
                    "kafka_consumer_error",
                    error=str(exc),
                    backoff_seconds=self._backoff,
                )
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)
            finally:
                if self._consumer:
                    try:
                        self._consumer.close()
                    except Exception:
                        pass
                    self._consumer = None

    async def _consume_loop(self) -> None:
        """Inner loop: poll → process → commit."""
        assert self._consumer is not None
        loop = asyncio.get_event_loop()
        pending_offsets: list[TopicPartition] = []
        last_lag_check = time.monotonic()

        while self._running:
            # Non-blocking poll via thread-pool to avoid blocking the event loop
            msg = await loop.run_in_executor(
                None, self._consumer.poll, _POLL_TIMEOUT
            )

            if msg is None:
                # No message within timeout — flush any pending batch
                await self._processor.flush_batch()
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(
                        "partition_eof",
                        partition=msg.partition(),
                        offset=msg.offset(),
                    )
                    await self._processor.flush_batch()
                    continue
                raise KafkaException(msg.error())

            # Deserialise
            try:
                raw: dict[str, Any] = json.loads(msg.value().decode())
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.error(
                    "message_deserialise_failed",
                    partition=msg.partition(),
                    offset=msg.offset(),
                    error=str(exc),
                )
                # Still commit so we don't get stuck on a poison pill
                self._consumer.commit(message=msg, asynchronous=True)
                continue

            # Run the processing pipeline
            await self._processor.process(raw)

            # Track offset for commit
            pending_offsets.append(
                TopicPartition(msg.topic(), msg.partition(), msg.offset() + 1)
            )

            # Commit after every message (at-least-once semantics)
            self._consumer.commit(message=msg, asynchronous=True)

            # Periodically update consumer-lag metrics
            if time.monotonic() - last_lag_check > 5:
                self._update_lag_metrics()
                last_lag_check = time.monotonic()

    def _update_lag_metrics(self) -> None:
        if self._consumer is None:
            return
        try:
            assignment = self._consumer.assignment()
            _high_offsets = self._consumer.get_watermark_offsets
            for tp in assignment:
                try:
                    lo, hi = self._consumer.get_watermark_offsets(tp, timeout=0.5)
                    committed = self._consumer.committed([tp], timeout=0.5)[0].offset
                    lag = max(0, hi - max(committed, lo))
                    kafka_consumer_lag.labels(partition=str(tp.partition)).set(lag)
                except Exception:
                    pass
        except Exception:
            pass

    async def stop(self) -> None:
        """Signal the consume loop to exit and flush remaining messages."""
        self._running = False
        await self._processor.flush_batch()
        logger.info("consumer_stopped")
