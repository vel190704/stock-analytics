#!/usr/bin/env python3
"""Initialize PostgreSQL/TimescaleDB and apply schema migrations."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg


def _asyncpg_dsn() -> str:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://stockuser:stockpass@postgres:5432/stockdb",
    )
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


async def wait_for_postgres(dsn: str, retries: int = 60, delay_s: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print(f"[init_db] postgres ready after {attempt} attempt(s)")
            return
        except Exception as exc:  # pragma: no cover - infrastructure wait path
            print(f"[init_db] waiting for postgres ({attempt}/{retries}): {exc}")
            await asyncio.sleep(delay_s)

    raise RuntimeError("postgres did not become ready in time")


async def ensure_timescale_extension(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        print("[init_db] ensured timescaledb extension")
    finally:
        await conn.close()


def run_alembic_upgrade() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    print(f"[init_db] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=repo_root, check=False)
    if result.returncode != 0:
        raise RuntimeError("alembic upgrade head failed")


async def main() -> None:
    dsn = _asyncpg_dsn()
    await wait_for_postgres(dsn)
    await ensure_timescale_extension(dsn)
    run_alembic_upgrade()
    print("[init_db] initialization complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"[init_db] error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
