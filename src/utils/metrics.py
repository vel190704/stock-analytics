from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Producer metrics
# ---------------------------------------------------------------------------

messages_produced_total = Counter(
    name="messages_produced_total",
    documentation="Total number of messages successfully produced to Kafka",
    labelnames=["ticker"],
)

# ---------------------------------------------------------------------------
# Consumer metrics
# ---------------------------------------------------------------------------

messages_consumed_total = Counter(
    name="messages_consumed_total",
    documentation="Total number of messages consumed from Kafka",
    labelnames=["ticker", "status"],  # status: success | error | duplicate
)

messages_dlq_total = Counter(
    name="messages_dlq_total",
    documentation="Total number of messages routed to the dead-letter queue",
    labelnames=["ticker", "reason"],
)

# ---------------------------------------------------------------------------
# Processing latency metrics
# ---------------------------------------------------------------------------

processing_duration_seconds = Histogram(
    name="processing_duration_seconds",
    documentation="Time spent in each stage of the processing pipeline",
    labelnames=["stage"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

db_write_duration_seconds = Histogram(
    name="db_write_duration_seconds",
    documentation="Time spent writing a batch of events to TimescaleDB",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ---------------------------------------------------------------------------
# Infrastructure / connectivity metrics
# ---------------------------------------------------------------------------

active_websocket_connections = Gauge(
    name="active_websocket_connections",
    documentation="Number of currently active WebSocket client connections",
)

kafka_consumer_lag = Gauge(
    name="kafka_consumer_lag",
    documentation="Approximate consumer lag per Kafka partition",
    labelnames=["partition"],
)
