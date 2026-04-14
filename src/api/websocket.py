"""WebSocket broadcaster for real-time stock event streaming.

Routes:
- /ws/stocks: receives all events
- /ws/stocks/{ticker}: receives only events for that ticker
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.utils.logger import get_logger
from src.utils.metrics import active_websocket_connections

logger = get_logger(__name__)


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class WebSocketBroadcaster:
    """Manages global and per-ticker websocket subscriptions."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, ticker: str | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            if ticker:
                room = self._rooms.setdefault(ticker.upper(), set())
                room.add(websocket)
            else:
                self._connections.add(websocket)
        active_websocket_connections.inc()
        logger.info(
            "websocket_connected",
            client=websocket.client,
            ticker=ticker,
            total=self.connection_count,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        removed = False
        async with self._lock:
            if websocket in self._connections:
                self._connections.discard(websocket)
                removed = True

            empty_rooms: list[str] = []
            for ticker, sockets in self._rooms.items():
                if websocket in sockets:
                    sockets.discard(websocket)
                    removed = True
                if not sockets:
                    empty_rooms.append(ticker)

            for ticker in empty_rooms:
                self._rooms.pop(ticker, None)

        if removed:
            active_websocket_connections.dec()
        logger.info(
            "websocket_disconnected",
            client=websocket.client,
            total=self.connection_count,
        )

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send *event* as JSON to all connected clients.

        Dead connections are silently dropped.
        """
        ticker = str(event.get("ticker", "")).upper()
        async with self._lock:
            global_connections = set(self._connections)
            room_connections = set(self._rooms.get(ticker, set()))

        targets = list(global_connections | room_connections)
        if not targets:
            return

        payload = json.dumps(event, cls=_JSONEncoder)
        dead: list[WebSocket] = []

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
                    for sockets in self._rooms.values():
                        sockets.discard(ws)
            active_websocket_connections.dec(len(dead))
            logger.debug("websocket_dead_connections_pruned", count=len(dead))

    @property
    def connection_count(self) -> int:
        room_total = sum(len(room) for room in self._rooms.values())
        return len(self._connections) + room_total


async def websocket_endpoint(
    websocket: WebSocket,
    broadcaster: WebSocketBroadcaster,
    ticker: str | None = None,
) -> None:
    """FastAPI WebSocket handler — injected with the app-level broadcaster."""
    await broadcaster.connect(websocket, ticker=ticker)
    try:
        # Keep the connection alive; the client can send pings or close it
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a ping to detect dead connections
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("websocket_error", error=str(exc))
    finally:
        await broadcaster.disconnect(websocket)
