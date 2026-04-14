"""Create stock_events hypertable with TimescaleDB.

Revision ID: 0001
Revises:
Create Date: 2025-06-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    op.create_table(
        "stock_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric(12, 4), nullable=True),
        sa.Column(
            "price_change",
            sa.Numeric(12, 4),
            sa.Computed("close - open", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "pct_change",
            sa.Numeric(8, 4),
            sa.Computed(
                "CASE WHEN open != 0 THEN ROUND(((close - open) / open) * 100, 4) ELSE NULL END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("source", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id", "event_time"),
    )

    op.create_index("ix_stock_events_ticker", "stock_events", ["ticker"])
    op.create_index(
        "ix_stock_events_ticker_event_time",
        "stock_events",
        ["ticker", "event_time"],
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('stock_events', 'event_time', "
        "if_not_exists => TRUE, migrate_data => TRUE);"
    )

    # Enable compression on chunks older than 7 days
    op.execute(
        "ALTER TABLE stock_events SET ("
        "timescaledb.compress, "
        "timescaledb.compress_segmentby = 'ticker'"
        ");"
    )
    op.execute(
        "SELECT add_compression_policy('stock_events', INTERVAL '7 days', if_not_exists => TRUE);"
    )

    # Continuous aggregate for 1-minute OHLCV
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS stock_ohlcv_1m
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 minute', event_time) AS bucket,
            ticker,
            first(open, event_time)  AS open,
            last(close, event_time)  AS close,
            max(high)                AS high,
            min(low)                 AS low,
            sum(volume)              AS volume
        FROM stock_events
        GROUP BY bucket, ticker
        WITH NO DATA;
        """
    )

    op.execute(
        "SELECT add_continuous_aggregate_policy('stock_ohlcv_1m', "
        "start_offset => INTERVAL '1 hour', "
        "end_offset   => INTERVAL '1 minute', "
        "schedule_interval => INTERVAL '1 minute', "
        "if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS stock_ohlcv_1m CASCADE;")
    op.drop_table("stock_events")
