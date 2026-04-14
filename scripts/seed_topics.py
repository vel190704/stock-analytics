#!/usr/bin/env python3
"""Create Kafka topics and optionally seed the pipeline with simulated data.

Usage:
    # Create topics only
    python scripts/seed_topics.py --topics-only

    # Create topics and produce 100 simulated events per ticker
    python scripts/seed_topics.py --seed-count 100
"""

import argparse
import asyncio
import sys
import time

from confluent_kafka.admin import AdminClient, NewTopic

TOPIC_CONFIGS = {
    "stock_prices": {
        "num_partitions": 6,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
            "compression.type": "snappy",
            "cleanup.policy": "delete",
        },
    },
    "stock_prices_dlq": {
        "num_partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(30 * 24 * 60 * 60 * 1000),  # 30 days
            "compression.type": "snappy",
            "cleanup.policy": "delete",
        },
    },
}


def create_topics(bootstrap_servers: str) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    # Check which topics already exist
    existing = set(admin.list_topics(timeout=10).topics.keys())
    topics_to_create = [
        NewTopic(
            name,
            num_partitions=cfg["num_partitions"],
            replication_factor=cfg["replication_factor"],
            config=cfg["config"],
        )
        for name, cfg in TOPIC_CONFIGS.items()
        if name not in existing
    ]

    if not topics_to_create:
        print("[seed_topics] All topics already exist.")
        return

    futures = admin.create_topics(topics_to_create)
    for topic, future in futures.items():
        try:
            future.result()
            print(f"[seed_topics] Created topic: {topic}")
        except Exception as exc:
            print(f"[seed_topics] ERROR creating topic {topic}: {exc}", file=sys.stderr)


async def seed_events(seed_count: int) -> None:
    from src.config.settings import settings
    from src.producer.data_source import SimulatedDataSource
    from src.producer.stock_producer import StockProducer

    print(f"[seed_topics] Seeding {seed_count} events per ticker...")
    producer = StockProducer()
    source = SimulatedDataSource()

    for i in range(seed_count):
        messages = await source.fetch_latest(settings.tickers)
        await producer.produce_batch(messages)
        if (i + 1) % 10 == 0:
            print(f"[seed_topics] Produced {(i + 1) * len(settings.tickers)} events...")
        await asyncio.sleep(0.05)  # small throttle

    remaining = await producer.flush(timeout=30)
    await producer.close()
    print(
        f"[seed_topics] Seeding complete. "
        f"Total events: {seed_count * len(settings.tickers)}. "
        f"Unflushed: {remaining}."
    )


def wait_for_kafka(bootstrap_servers: str, retries: int = 30, delay: float = 2.0) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    for attempt in range(1, retries + 1):
        try:
            meta = admin.list_topics(timeout=5)
            if meta:
                print(f"[seed_topics] Kafka is ready (attempt {attempt})")
                return
        except Exception as exc:
            print(f"[seed_topics] Waiting for Kafka... ({attempt}/{retries}) — {exc}")
            time.sleep(delay)
    print("[seed_topics] ERROR: Kafka never became available.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kafka topic setup and data seeding")
    parser.add_argument("--topics-only", action="store_true", help="Only create topics, skip seeding")
    parser.add_argument("--seed-count", type=int, default=50, help="Number of batches to produce per ticker")
    args = parser.parse_args()

    from src.config.settings import settings

    wait_for_kafka(settings.kafka_bootstrap_servers)
    create_topics(settings.kafka_bootstrap_servers)

    if not args.topics_only:
        asyncio.run(seed_events(args.seed_count))


if __name__ == "__main__":
    main()
