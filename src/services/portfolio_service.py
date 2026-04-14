from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Position, StockEvent, Trade


class PortfolioService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def _get_latest_price(self, session: AsyncSession, ticker: str) -> tuple[Decimal | None, Decimal | None]:
        cached = await self._redis.get(f"latest:{ticker}")
        if cached:
            data = json.loads(cached)
            price = Decimal(str(data.get("close", "0")))
            price_change = Decimal(str(data.get("price_change", "0")))
            return price, price_change

        stmt = (
            select(StockEvent)
            .where(StockEvent.ticker == ticker)
            .order_by(desc(StockEvent.event_time))
            .limit(1)
        )
        row = await session.execute(stmt)
        event = row.scalar_one_or_none()
        if not event:
            return None, None
        return event.close, event.price_change

    async def add_position(
        self,
        session: AsyncSession,
        ticker: str,
        quantity: Decimal,
        cost_basis: Decimal,
    ) -> Position:
        position = Position(
            ticker=ticker.upper(),
            quantity=quantity,
            cost_basis=cost_basis,
        )
        session.add(position)
        await session.flush()
        return position

    async def close_position(self, session: AsyncSession, position_id: int) -> bool:
        position = await session.get(Position, position_id)
        if not position:
            return False
        await session.delete(position)
        return True

    async def record_trade(
        self,
        session: AsyncSession,
        ticker: str,
        action: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Trade:
        trade = Trade(
            ticker=ticker.upper(),
            action=action.upper(),
            quantity=quantity,
            price=price,
        )
        session.add(trade)
        await session.flush()
        return trade

    async def list_trades(self, session: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[int, list[Trade]]:
        offset = (page - 1) * page_size
        total = len((await session.execute(select(Trade.id))).scalars().all())
        stmt = select(Trade).order_by(desc(Trade.executed_at)).offset(offset).limit(page_size)
        rows = await session.execute(stmt)
        return total, list(rows.scalars().all())

    async def get_positions_with_pnl(self, session: AsyncSession) -> list[dict[str, Any]]:
        rows = await session.execute(select(Position).order_by(desc(Position.opened_at)))
        positions = list(rows.scalars().all())

        result: list[dict[str, Any]] = []
        for pos in positions:
            latest_price, daily_price_change = await self._get_latest_price(session, pos.ticker)
            if latest_price is None:
                latest_price = pos.cost_basis
            market_value = (latest_price * pos.quantity).quantize(Decimal("0.0001"))
            invested = (pos.cost_basis * pos.quantity).quantize(Decimal("0.0001"))
            unrealized_pnl = (market_value - invested).quantize(Decimal("0.0001"))
            pnl_pct = Decimal("0")
            if invested != 0:
                pnl_pct = ((unrealized_pnl / invested) * Decimal("100")).quantize(Decimal("0.0001"))

            daily_change = Decimal("0")
            if daily_price_change is not None:
                daily_change = (daily_price_change * pos.quantity).quantize(Decimal("0.0001"))

            result.append(
                {
                    "id": pos.id,
                    "ticker": pos.ticker,
                    "quantity": pos.quantity,
                    "cost_basis": pos.cost_basis,
                    "current_price": latest_price,
                    "market_value": market_value,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_pct": pnl_pct,
                    "daily_change": daily_change,
                    "opened_at": pos.opened_at,
                }
            )
        return result

    async def get_portfolio_summary(self, session: AsyncSession) -> dict[str, Any]:
        cache_key = "portfolio:summary"
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        positions = await self.get_positions_with_pnl(session)
        total_invested = sum(Decimal(str(p["cost_basis"])) * Decimal(str(p["quantity"])) for p in positions)
        total_value = sum(Decimal(str(p["market_value"])) for p in positions)
        total_pnl = total_value - total_invested
        daily_change = sum(Decimal(str(p["daily_change"])) for p in positions)

        best = None
        worst = None
        if positions:
            best = max(positions, key=lambda p: Decimal(str(p["pnl_pct"])))
            worst = min(positions, key=lambda p: Decimal(str(p["pnl_pct"])))

        payload = {
            "total_positions": len(positions),
            "total_invested": float(total_invested),
            "total_value": float(total_value),
            "total_pnl": float(total_pnl),
            "daily_change": float(daily_change),
            "best_position": best,
            "worst_position": worst,
        }

        await self._redis.set(cache_key, json.dumps(payload, default=str), ex=5)
        return payload
