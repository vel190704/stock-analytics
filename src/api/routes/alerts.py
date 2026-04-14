from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.middleware import post_limit
from src.api.dependencies import get_alert_service, get_session
from src.services.alert_service import AlertRule as AlertRuleIn
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleCreate(BaseModel):
    ticker: str
    condition: str
    threshold: Decimal
    user_email: EmailStr


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    condition: str
    threshold: Decimal
    user_email: EmailStr
    is_active: bool
    created_at: datetime


class AlertHistoryResponse(BaseModel):
    id: int
    ticker: str
    rule_id: int
    triggered_price: Decimal
    condition: str
    ai_summary: str
    fired_at: datetime


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
@post_limit()
async def create_alert_rule(
    request: Request,
    payload: AlertRuleCreate,
    service: Annotated[AlertService, Depends(get_alert_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    _: dict = Depends(get_current_user),
) -> AlertRuleResponse:
    rule = await service.create_rule(session, AlertRuleIn(**payload.model_dump()))
    return AlertRuleResponse.model_validate(rule)


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    service: Annotated[AlertService, Depends(get_alert_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AlertRuleResponse]:
    rows = await service.list_rules(session)
    return [AlertRuleResponse.model_validate(row) for row in rows]


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    service: Annotated[AlertService, Depends(get_alert_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    deleted = await service.delete_rule(session, rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")


@router.get("/history", response_model=list[AlertHistoryResponse])
async def alert_history(
    service: Annotated[AlertService, Depends(get_alert_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AlertHistoryResponse]:
    rows = await service.list_history(session, limit=limit)
    return [AlertHistoryResponse(**row) for row in rows]


@router.get("/history/{ticker}", response_model=list[AlertHistoryResponse])
async def alert_history_for_ticker(
    ticker: str,
    service: Annotated[AlertService, Depends(get_alert_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AlertHistoryResponse]:
    rows = await service.list_history(session, ticker=ticker.upper(), limit=limit)
    return [AlertHistoryResponse(**row) for row in rows]
