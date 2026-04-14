from __future__ import annotations

import asyncio
import json
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from redis.asyncio import Redis
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.db import AsyncSessionFactory
from src.database.models import AlertFired, AlertRule as ORMAlertRule
from src.services.claude_service import AlertEventContext, analyse_price_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertRule(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str = Field(min_length=1, max_length=10)
    condition: str = Field(pattern="^(above|below|pct_change_exceeds)$")
    threshold: Decimal
    user_email: EmailStr

    @field_validator("ticker")
    @classmethod
    def normalise_ticker(cls, value: str) -> str:
        return value.upper()


class AlertRuleOut(BaseModel):
    id: int
    ticker: str
    condition: str
    threshold: Decimal
    user_email: EmailStr
    is_active: bool
    created_at: datetime


class AlertFiredOut(BaseModel):
    id: int
    ticker: str
    rule_id: int
    triggered_price: Decimal
    ai_summary: str
    fired_at: datetime


@dataclass(slots=True)
class EvaluatedRule:
    rule: ORMAlertRule
    pct_change: float


class AlertService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _redis_key(ticker: str) -> str:
        return f"alerts:{ticker.upper()}"

    async def _cache_rule(self, rule: ORMAlertRule) -> None:
        payload = json.dumps(
            {
                "id": rule.id,
                "ticker": rule.ticker,
                "condition": rule.condition,
                "threshold": str(rule.threshold),
                "user_email": rule.user_email,
                "is_active": rule.is_active,
            }
        )
        await self._redis.hset(self._redis_key(rule.ticker), str(rule.id), payload)

    async def _remove_cached_rule(self, ticker: str, rule_id: int) -> None:
        await self._redis.hdel(self._redis_key(ticker), str(rule_id))

    async def create_rule(self, session: AsyncSession, payload: AlertRule) -> ORMAlertRule:
        rule = ORMAlertRule(
            ticker=payload.ticker,
            condition=payload.condition,
            threshold=payload.threshold,
            user_email=str(payload.user_email),
            is_active=True,
        )
        session.add(rule)
        await session.flush()
        await self._cache_rule(rule)
        return rule

    async def list_rules(self, session: AsyncSession) -> list[ORMAlertRule]:
        stmt = select(ORMAlertRule).order_by(desc(ORMAlertRule.created_at))
        rows = await session.execute(stmt)
        return list(rows.scalars().all())

    async def delete_rule(self, session: AsyncSession, rule_id: int) -> bool:
        existing = await session.get(ORMAlertRule, rule_id)
        if not existing:
            return False
        ticker = existing.ticker
        await session.execute(delete(ORMAlertRule).where(ORMAlertRule.id == rule_id))
        await self._remove_cached_rule(ticker, rule_id)
        return True

    async def list_history(
        self,
        session: AsyncSession,
        ticker: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        stmt = (
            select(
                AlertFired.id,
                AlertFired.ticker,
                AlertFired.rule_id,
                AlertFired.triggered_price,
                AlertFired.ai_summary,
                AlertFired.fired_at,
                ORMAlertRule.condition,
            )
            .join(ORMAlertRule, ORMAlertRule.id == AlertFired.rule_id)
        )
        if ticker:
            stmt = stmt.where(AlertFired.ticker == ticker.upper())
        stmt = stmt.order_by(desc(AlertFired.fired_at)).limit(limit)
        rows = await session.execute(stmt)
        return [dict(item) for item in rows.mappings().all()]

    async def _load_active_rules(self, session: AsyncSession, ticker: str) -> list[ORMAlertRule]:
        key = self._redis_key(ticker)
        cached = await self._redis.hvals(key)
        if cached:
            rules: list[ORMAlertRule] = []
            for raw in cached:
                item = json.loads(raw)
                if not item.get("is_active", True):
                    continue
                rules.append(
                    ORMAlertRule(
                        id=int(item["id"]),
                        ticker=item["ticker"],
                        condition=item["condition"],
                        threshold=Decimal(item["threshold"]),
                        user_email=item["user_email"],
                        is_active=True,
                    )
                )
            return rules

        stmt = select(ORMAlertRule).where(
            ORMAlertRule.ticker == ticker.upper(),
            ORMAlertRule.is_active.is_(True),
        )
        rows = await session.execute(stmt)
        db_rules = list(rows.scalars().all())
        for rule in db_rules:
            await self._cache_rule(rule)
        return db_rules

    @staticmethod
    def _is_triggered(rule: ORMAlertRule, close: Decimal, pct_change: float) -> bool:
        threshold = float(rule.threshold)
        if rule.condition == "above":
            return float(close) > threshold
        if rule.condition == "below":
            return float(close) < threshold
        if rule.condition == "pct_change_exceeds":
            return abs(pct_change) >= threshold
        return False

    @staticmethod
    async def _send_email(to_email: str, subject: str, html_body: str) -> None:
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            logger.info("smtp_not_configured_alert_skipped", to_email=to_email)
            return

        def _send() -> None:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.alert_email_from
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.alert_email_from, [to_email], msg.as_string())

        await asyncio.to_thread(_send)

    async def process_stock_event(self, event: dict[str, object]) -> None:
        ticker = str(event.get("ticker", "")).upper()
        if not ticker:
            return

        close = Decimal(str(event.get("close", "0")))
        open_price = Decimal(str(event.get("open", "0")))
        volume = int(event.get("volume", 0))
        vwap_raw = event.get("vwap")
        vwap = float(vwap_raw) if vwap_raw is not None else None

        pct_change = 0.0
        if open_price != 0:
            pct_change = float(((close - open_price) / open_price) * Decimal("100"))

        async with AsyncSessionFactory() as session:
            try:
                rules = await self._load_active_rules(session, ticker)
                if not rules:
                    return

                for rule in rules:
                    if not self._is_triggered(rule, close, pct_change):
                        continue

                    context = AlertEventContext(
                        close=float(close),
                        pct_change=pct_change,
                        volume=volume,
                        vwap=vwap,
                    )
                    ai_summary = await analyse_price_event(ticker, context, rule)
                    fired = AlertFired(
                        ticker=ticker,
                        rule_id=rule.id,
                        triggered_price=close,
                        ai_summary=ai_summary,
                    )
                    session.add(fired)

                    fired_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    html_body = (
                        f"<h3>Stock Alert Triggered: {ticker}</h3>"
                        f"<p><b>Condition:</b> {rule.condition} {rule.threshold}</p>"
                        f"<p><b>Triggered price:</b> ${float(close):.2f}</p>"
                        f"<p><b>Time:</b> {fired_at}</p>"
                        f"<blockquote>{ai_summary}</blockquote>"
                    )
                    await self._send_email(
                        to_email=rule.user_email,
                        subject=f"[{ticker}] Price alert fired",
                        html_body=html_body,
                    )

                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("alert_processing_failed", ticker=ticker, error=str(exc))
