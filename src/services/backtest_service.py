from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import sqrt
from typing import Any

import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import select

from src.database.db import AsyncSessionFactory
from src.database.models import StockEvent


@dataclass
class BacktestResult:
    ticker: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(period, min_periods=period).mean()
    avg_loss = losses.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _generate_signals(df: pd.DataFrame, strategy: str, params: dict[str, Any]) -> pd.Series:
    signals = pd.Series(0, index=df.index, dtype="int64")

    if strategy == "ma_crossover":
        fast_window = int(params.get("fast_window", 10))
        slow_window = int(params.get("slow_window", 20))
        fast_ma = df["close"].rolling(fast_window, min_periods=fast_window).mean()
        slow_ma = df["close"].rolling(slow_window, min_periods=slow_window).mean()
        buy_cross = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
        sell_cross = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
        signals.loc[buy_cross] = 1
        signals.loc[sell_cross] = -1
    elif strategy == "rsi_oversold":
        rsi_period = int(params.get("rsi_period", 14))
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        rsi = _compute_rsi(df["close"], period=rsi_period)
        signals.loc[rsi < oversold] = 1
        signals.loc[rsi > overbought] = -1
    elif strategy == "breakout":
        lookback = int(params.get("lookback", 20))
        rolling_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        breakout = df["close"] > rolling_high
        signals.loc[breakout] = 1
        exit_signal = df["close"] < df["close"].rolling(lookback, min_periods=lookback).mean()
        signals.loc[exit_signal] = -1
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    return signals


async def run_backtest(
    ticker: str,
    strategy: str,
    params: dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 10000.0,
) -> BacktestResult:
    """Run a strategy backtest against historical stock_events data."""
    async with AsyncSessionFactory() as session:
        stmt = (
            select(
                StockEvent.event_time,
                StockEvent.open,
                StockEvent.high,
                StockEvent.low,
                StockEvent.close,
                StockEvent.volume,
            )
            .where(
                StockEvent.ticker == ticker.upper(),
                StockEvent.event_time >= start_date,
                StockEvent.event_time <= end_date,
            )
            .order_by(StockEvent.event_time.asc())
        )
        rows = (await session.execute(stmt)).all()

    if not rows:
        return BacktestResult(
            ticker=ticker.upper(),
            strategy=strategy,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            initial_capital=initial_capital,
            final_value=initial_capital,
            total_return_pct=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            total_trades=0,
            trades=[],
            equity_curve=[],
        )

    df = pd.DataFrame(
        [
            {
                "event_time": r.event_time,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": int(r.volume),
            }
            for r in rows
        ]
    )

    signals = _generate_signals(df, strategy, params)

    commission = 0.001
    cash = float(initial_capital)
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []

    benchmark_start = float(df.iloc[0]["close"])
    for i, row in df.iterrows():
        price = float(row["close"])
        signal = int(signals.iloc[i])

        if signal == 1 and shares == 0.0 and cash > 0.0:
            shares = cash / (price * (1 + commission))
            invested_value = shares * price
            cash = 0.0
            trades.append(
                {
                    "date": pd.Timestamp(row["event_time"]).isoformat(),
                    "action": "BUY",
                    "price": price,
                    "shares": shares,
                    "value": invested_value,
                }
            )
        elif signal == -1 and shares > 0.0:
            sale_value = shares * price * (1 - commission)
            trades.append(
                {
                    "date": pd.Timestamp(row["event_time"]).isoformat(),
                    "action": "SELL",
                    "price": price,
                    "shares": shares,
                    "value": sale_value,
                }
            )
            cash = sale_value
            shares = 0.0

        equity_value = cash + (shares * price)
        benchmark_value = initial_capital * (price / benchmark_start)
        equity_curve.append(
            {
                "date": pd.Timestamp(row["event_time"]).isoformat(),
                "value": round(equity_value, 4),
                "benchmark_value": round(benchmark_value, 4),
            }
        )

    final_value = equity_curve[-1]["value"] if equity_curve else initial_capital
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    curve_df = pd.DataFrame(equity_curve)
    returns = curve_df["value"].pct_change().fillna(0.0)
    returns_std = float(returns.std())
    returns_mean = float(returns.mean())
    sharpe_ratio = (sqrt(252) * returns_mean / returns_std) if returns_std > 0 else 0.0

    running_max = curve_df["value"].cummax()
    drawdown = (curve_df["value"] - running_max) / running_max.replace(0, pd.NA)
    max_drawdown_pct = float(drawdown.min()) * 100 if not drawdown.empty else 0.0

    trade_pnls: list[float] = []
    pending_buy: float | None = None
    for trade in trades:
        if trade["action"] == "BUY":
            pending_buy = float(trade["value"])
        elif trade["action"] == "SELL" and pending_buy is not None:
            trade_pnls.append(float(trade["value"]) - pending_buy)
            pending_buy = None
    win_rate = (sum(1 for pnl in trade_pnls if pnl > 0) / len(trade_pnls) * 100) if trade_pnls else 0.0

    return BacktestResult(
        ticker=ticker.upper(),
        strategy=strategy,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        initial_capital=float(initial_capital),
        final_value=float(final_value),
        total_return_pct=float(total_return_pct),
        sharpe_ratio=float(round(sharpe_ratio, 4)),
        max_drawdown_pct=float(round(max_drawdown_pct, 4)),
        win_rate=float(round(win_rate, 2)),
        total_trades=len(trades),
        trades=trades,
        equity_curve=equity_curve,
    )


async def store_backtest_result(redis: Redis, result: BacktestResult) -> None:
    key = "backtest:results"
    await redis.lpush(key, json.dumps(asdict(result), default=str))
    await redis.ltrim(key, 0, 9)


async def list_backtest_results(redis: Redis) -> list[dict[str, Any]]:
    rows = await redis.lrange("backtest:results", 0, 9)
    return [json.loads(row) for row in rows]
