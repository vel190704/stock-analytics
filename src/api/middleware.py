from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def get_limit():
    return limiter.limit("60/minute")


def post_limit():
    return limiter.limit("10/minute")


async def _rate_limit_exceeded_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    response = JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )
    # Use the window size from the limit string when possible.
    limit_str = str(exc.detail)
    retry_after = 60
    if "minute" in limit_str:
        retry_after = 60
    elif "second" in limit_str:
        retry_after = 1
    response.headers["Retry-After"] = str(retry_after)
    return response


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
