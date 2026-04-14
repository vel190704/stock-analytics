from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.middleware import post_limit
from src.api.dependencies import get_portfolio_service, get_session
from src.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PositionCreate(BaseModel):
    ticker: str
    quantity: Decimal
    cost_basis: Decimal


class TradeCreate(BaseModel):
    ticker: str
    action: str
    quantity: Decimal
    price: Decimal


class PositionResponse(BaseModel):
    id: int
    ticker: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    pnl_pct: Decimal
    daily_change: Decimal
    opened_at: datetime


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    action: str
    quantity: Decimal
    price: Decimal
    total: Decimal
    executed_at: datetime


class TradeHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[TradeResponse]


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
@post_limit()
async def add_position(
    request: Request,
    payload: PositionCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    _: dict = Depends(get_current_user),
) -> PositionResponse:
    position = await service.add_position(
        session,
        ticker=payload.ticker,
        quantity=payload.quantity,
        cost_basis=payload.cost_basis,
    )
    rows = await service.get_positions_with_pnl(session)
    item = next((row for row in rows if row["id"] == position.id), None)
    if not item:
        raise HTTPException(status_code=500, detail="Position creation succeeded but could not load P&L")
    return PositionResponse(**item)


@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PositionResponse]:
    rows = await service.get_positions_with_pnl(session)
    return [PositionResponse(**row) for row in rows]


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_position(
    position_id: int,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    deleted = await service.close_position(session, position_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")


@router.post("/trades", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
@post_limit()
async def create_trade(
    request: Request,
    payload: TradeCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    _: dict = Depends(get_current_user),
) -> TradeResponse:
    if payload.action.upper() not in {"BUY", "SELL"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="action must be BUY or SELL")
    trade = await service.record_trade(
        session,
        ticker=payload.ticker,
        action=payload.action,
        quantity=payload.quantity,
        price=payload.price,
    )
    return TradeResponse.model_validate(trade)


@router.get("/trades", response_model=TradeHistoryResponse)
async def list_trades(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TradeHistoryResponse:
    total, rows = await service.list_trades(session, page=page, page_size=page_size)
    return TradeHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[TradeResponse.model_validate(row) for row in rows],
    )


@router.get("/summary")
async def portfolio_summary(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    return await service.get_portfolio_summary(session)
