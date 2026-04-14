from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.middleware import post_limit
from src.database.models import SentimentScore
from src.services.sentiment_service import fetch_and_score_sentiment

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


class SentimentScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    headline: str
    score: Decimal
    label: str
    reason: str
    source_url: str
    scored_at: datetime


@router.get('/leaderboard')
async def sentiment_leaderboard(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(
            SentimentScore.ticker,
            func.avg(SentimentScore.score).label('avg_score'),
            func.count(SentimentScore.id).label('sample_size'),
        )
        .where(SentimentScore.scored_at >= cutoff)
        .group_by(SentimentScore.ticker)
        .order_by(desc('avg_score'))
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            'ticker': row.ticker,
            'avg_score': float(row.avg_score),
            'sample_size': int(row.sample_size),
        }
        for row in rows
    ]


@router.get('/{ticker}/aggregate')
async def aggregate_sentiment(
    ticker: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    now = datetime.now(timezone.utc)

    async def avg_for_window(days: int) -> float | None:
        start = now - timedelta(days=days)
        stmt = select(func.avg(SentimentScore.score)).where(
            SentimentScore.ticker == ticker.upper(),
            SentimentScore.scored_at >= start,
        )
        value = (await session.execute(stmt)).scalar_one_or_none()
        return float(value) if value is not None else None

    return {
        'ticker': ticker.upper(),
        'avg_24h': await avg_for_window(1),
        'avg_7d': await avg_for_window(7),
        'avg_30d': await avg_for_window(30),
    }


@router.post('/{ticker}/refresh')
@post_limit()
async def refresh_sentiment(
    request: Request,
    ticker: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    scored = await fetch_and_score_sentiment(ticker.upper())
    if not scored:
        raise HTTPException(status_code=404, detail='No sentiment data available for ticker')

    inserted = 0
    for item in scored:
        record = SentimentScore(
            ticker=ticker.upper(),
            headline=item.headline,
            score=item.score,
            label=item.label,
            reason=item.reason,
            source_url=item.source_url,
        )
        session.add(record)
        inserted += 1

    return {'ticker': ticker.upper(), 'inserted': inserted}


@router.get('/{ticker}', response_model=list[SentimentScoreResponse])
async def sentiment_for_ticker(
    ticker: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SentimentScoreResponse]:
    stmt = (
        select(SentimentScore)
        .where(SentimentScore.ticker == ticker.upper())
        .order_by(desc(SentimentScore.scored_at))
        .limit(20)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [SentimentScoreResponse.model_validate(row) for row in rows]
