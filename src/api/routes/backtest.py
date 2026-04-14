from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from src.api.auth import get_current_user
from src.api.dependencies import get_redis
from src.api.middleware import post_limit
from src.services.backtest_service import list_backtest_results, run_backtest, store_backtest_result

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRunRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    strategy: str = Field(pattern="^(ma_crossover|rsi_oversold|breakout)$")
    params: dict[str, Any] = Field(default_factory=dict)
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000.0, gt=0)


@router.post("/run")
@post_limit()
async def run_backtest_endpoint(
    request: Request,
    payload: BacktestRunRequest,
    redis: Annotated[Redis, Depends(get_redis)],
    _: dict = Depends(get_current_user),
) -> dict[str, Any]:
    result = await run_backtest(
        ticker=payload.ticker.upper(),
        strategy=payload.strategy,
        params=payload.params,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
    )
    await store_backtest_result(redis, result)
    return result.__dict__


@router.get("/results")
async def recent_backtests(
    redis: Annotated[Redis, Depends(get_redis)],
) -> list[dict[str, Any]]:
    return await list_backtest_results(redis)
