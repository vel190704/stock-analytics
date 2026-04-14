from decimal import Decimal
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    TIMESTAMP,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StockEvent(Base):
    """
    ORM model for the ``stock_events`` TimescaleDB hypertable.

    The table is partitioned by ``event_time`` (the hypertable dimension) and
    the primary key therefore includes both ``id`` and ``event_time`` as
    required by TimescaleDB.

    ``price_change`` and ``pct_change`` are database-generated computed
    columns; they are read-only from the ORM perspective.
    """

    __tablename__ = "stock_events"

    # Primary key is composite (id, event_time) to satisfy TimescaleDB
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )

    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Computed columns — populated by the database, never written by the ORM
    price_change: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        Computed("close - open", persisted=True),
        nullable=True,
    )
    pct_change: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4),
        Computed(
            "CASE WHEN open != 0 THEN ROUND(((close - open) / open) * 100, 4) ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<StockEvent ticker={self.ticker!r} "
            f"close={self.close} event_time={self.event_time}>"
        )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(30), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AlertFired(Base):
    __tablename__ = "alerts_fired"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    triggered_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        Computed("quantity * price", persisted=True),
        nullable=False,
    )
    executed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    label: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        server_default=func.now(),
        nullable=False,
    )
