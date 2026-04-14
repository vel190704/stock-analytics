from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.api.middleware import post_limit
from src.config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _build_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.post("/register")
@post_limit()
async def register(request: Request, payload: dict[str, str]) -> dict[str, str]:
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password are required")

    redis = request.app.state.redis
    existing = await redis.hget("auth:users", email)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed = pwd_context.hash(password)
    await redis.hset(
        "auth:users",
        email,
        json.dumps({"email": email, "password_hash": hashed}),
    )

    token = _build_token(email)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
@post_limit()
async def login(request: Request, payload: dict[str, str]) -> dict[str, str]:
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    redis = request.app.state.redis
    raw_user = await redis.hget("auth:users", email)
    if not raw_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = json.loads(raw_user)
    if not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _build_token(email)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        if not email:
            raise credentials_error
    except JWTError:
        raise credentials_error from None

    redis = request.app.state.redis
    raw_user = await redis.hget("auth:users", email)
    if not raw_user:
        raise credentials_error

    return {"email": email}
