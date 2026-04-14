"""Create Phase 2 tables for alerts, portfolio, sentiment.

Revision ID: 0002_phase2_tables
Revises: 0001_initial
Create Date: 2026-04-13 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase2_tables"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("condition", sa.String(length=30), nullable=False),
        sa.Column("threshold", sa.Numeric(12, 4), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_alert_rules_ticker", "alert_rules", ["ticker"])

    op.create_table(
        "alerts_fired",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("fired_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_alerts_fired_ticker", "alerts_fired", ["ticker"])

    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("cost_basis", sa.Numeric(12, 4), nullable=False),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_positions_ticker", "positions", ["ticker"])

    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("action", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("total", sa.Numeric(14, 4), sa.Computed("quantity * price", persisted=True), nullable=False),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_trades_ticker", "trades", ["ticker"])

    op.create_table(
        "sentiment_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("label", sa.String(length=10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("scored_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id", "scored_at"),
    )
    op.create_index("ix_sentiment_scores_ticker", "sentiment_scores", ["ticker"])

    op.execute(
        "SELECT create_hypertable('sentiment_scores', 'scored_at', "
        "if_not_exists => TRUE, migrate_data => TRUE);"
    )


def downgrade() -> None:
    op.drop_index("ix_sentiment_scores_ticker", table_name="sentiment_scores")
    op.drop_table("sentiment_scores")

    op.drop_index("ix_trades_ticker", table_name="trades")
    op.drop_table("trades")

    op.drop_index("ix_positions_ticker", table_name="positions")
    op.drop_table("positions")

    op.drop_index("ix_alerts_fired_ticker", table_name="alerts_fired")
    op.drop_table("alerts_fired")

    op.drop_index("ix_alert_rules_ticker", table_name="alert_rules")
    op.drop_table("alert_rules")
