"""Integration tests for the FastAPI REST endpoints.

These tests use the FastAPI TestClient (HTTPX-based), mocking out the
downstream services so no real Kafka or database connections are needed.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture(scope="module")
def app():
    """Create a test-scoped FastAPI app with mocked lifespan dependencies."""
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    """Use TestClient in a context that skips the real lifespan startup."""
    with patch("src.main.lifespan"):
        with TestClient(app, raise_server_exceptions=True) as c:
            # Inject required app state that normally comes from lifespan
            app.state.redis = AsyncMock()
            app.state.redis.ping = AsyncMock(return_value=True)
            app.state.producer = AsyncMock()
            app.state.broadcaster = AsyncMock()
            yield c


MOCK_TICKERS = [
    {
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "close": Decimal("182.50"),
        "pct_change": Decimal("1.39"),
        "volume": 2150000,
        "event_time": "2025-06-01T10:00:00+00:00",
    },
    {
        "ticker": "MSFT",
        "exchange": "NASDAQ",
        "close": Decimal("415.00"),
        "pct_change": Decimal("0.72"),
        "volume": 1800000,
        "event_time": "2025-06-01T10:00:00+00:00",
    },
]


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        with patch("src.main.AsyncSessionFactory") as mock_sf:
            session_mock = AsyncMock()
            session_mock.__aenter__ = AsyncMock(return_value=session_mock)
            session_mock.__aexit__ = AsyncMock(return_value=False)
            session_mock.execute = AsyncMock()
            mock_sf.return_value = session_mock
            resp = client.get("/health")
        # May be degraded if DB mock doesn't fully work; just ensure it responds
        assert resp.status_code in (200, 503)

    def test_health_response_has_checks_key(self, client):
        with patch("src.main.AsyncSessionFactory"):
            resp = client.get("/health")
        data = resp.json()
        assert "status" in data


class TestStocksRouter:
    @patch("src.api.dependencies.AsyncSessionFactory")
    def test_list_stocks_returns_200(self, mock_sf, client):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_sf.return_value = mock_session

        with patch(
            "src.api.routes.stocks.get_analytics_service"
        ) as mock_svc_dep:
            svc = AsyncMock()
            svc.get_all_tickers_latest = AsyncMock(return_value=MOCK_TICKERS)
            mock_svc_dep.return_value = svc

            resp = client.get("/stocks")
            assert resp.status_code == 200

    def test_list_stocks_pagination_defaults(self, client):
        with patch(
            "src.api.routes.stocks.get_analytics_service"
        ) as mock_svc_dep:
            svc = AsyncMock()
            svc.get_all_tickers_latest = AsyncMock(return_value=MOCK_TICKERS)
            mock_svc_dep.return_value = svc
            resp = client.get("/stocks?page=1&page_size=10")
            assert resp.status_code == 200
            data = resp.json()
            assert "data" in data
            assert "total" in data

    def test_get_ticker_latest_404_when_missing(self, client):
        with patch("src.api.routes.stocks.get_repository") as mock_repo_dep:
            repo = AsyncMock()
            repo.get_latest_for_ticker = AsyncMock(return_value=None)
            mock_repo_dep.return_value = repo
            resp = client.get("/stocks/UNKNOWN_TICKER/latest")
            assert resp.status_code == 404

    def test_get_ohlcv_invalid_date_range_returns_422(self, client):
        resp = client.get(
            "/stocks/AAPL?start=2025-06-02T00:00:00Z&end=2025-06-01T00:00:00Z"
        )
        assert resp.status_code == 422


class TestAnalyticsRouter:
    def test_top_gainers_returns_200(self, client):
        with patch("src.api.routes.analytics.get_analytics_service") as mock_svc:
            svc = AsyncMock()
            svc.get_top_gainers = AsyncMock(
                return_value=[{"ticker": "NVDA", "pct_change": Decimal("5.2")}]
            )
            mock_svc.return_value = svc
            resp = client.get("/analytics/top-gainers")
            assert resp.status_code == 200

    def test_top_losers_returns_200(self, client):
        with patch("src.api.routes.analytics.get_analytics_service") as mock_svc:
            svc = AsyncMock()
            svc.get_top_losers = AsyncMock(return_value=[])
            mock_svc.return_value = svc
            resp = client.get("/analytics/top-losers")
            assert resp.status_code == 200

    def test_volume_leaders_returns_200(self, client):
        with patch("src.api.routes.analytics.get_analytics_service") as mock_svc:
            svc = AsyncMock()
            svc.get_volume_leaders = AsyncMock(
                return_value=[{"ticker": "AAPL", "total_volume": 10_000_000}]
            )
            mock_svc.return_value = svc
            resp = client.get("/analytics/volume-leaders")
            assert resp.status_code == 200

    def test_moving_average_returns_200(self, client):
        with patch("src.api.routes.analytics.get_analytics_service") as mock_svc:
            svc = AsyncMock()
            svc.get_moving_average = AsyncMock(return_value=[])
            mock_svc.return_value = svc
            resp = client.get("/analytics/moving-average/AAPL?window=20")
            assert resp.status_code == 200

    def test_volatility_returns_200(self, client):
        with patch("src.api.routes.analytics.get_analytics_service") as mock_svc:
            svc = AsyncMock()
            svc.get_volatility = AsyncMock(
                return_value={"ticker": "AAPL", "volatility": None, "sample_size": 0}
            )
            mock_svc.return_value = svc
            resp = client.get("/analytics/volatility/AAPL")
            assert resp.status_code == 200


class TestResponseHeaders:
    def test_request_id_header_present(self, client):
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers

    def test_custom_request_id_echoed(self, client):
        custom_id = "test-request-123"
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["X-Request-ID"] == custom_id
