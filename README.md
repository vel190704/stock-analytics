# Stock Analytics Pipeline V2

Real-time stock analytics platform built on FastAPI, Kafka, TimescaleDB, Redis, Prometheus, and Grafana with a React dashboard.

This project is configured to use live sources first. Simulated data is disabled by default.

## Architecture

1. Producer fetches market updates (Polygon/yfinance live paths).
2. Producer publishes to Kafka topic `stock_prices`.
3. Consumer validates, deduplicates, enriches, and persists into TimescaleDB.
4. FastAPI exposes REST and WebSocket APIs from persisted data.
5. Dashboard reads from API and live websocket stream.
6. Prometheus scrapes metrics and Grafana visualizes them.

## Stack Services

1. API: http://localhost:8000
2. API docs: http://localhost:8000/docs
3. Kafka UI: http://localhost:8080
4. Prometheus: http://localhost:9090
5. Grafana: http://localhost:3000 (admin/admin)

## Quick Start

```bash
cd ~/project/stock_market
cp .env.example .env
make up
# wait for infra to become healthy
make seed
```

`make seed` runs DB initialization/migrations and creates Kafka topics without injecting fake market events.

## Run Dashboard Locally

```bash
cd ~/project/stock_market/dashboard
cp .env.example .env
# ensure this line exists in dashboard/.env
# VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

## Health Verification

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stocks
```

Expected:

1. `/health` returns `status: ok` or `status: degraded` with checks.
2. `/stocks` returns data persisted in TimescaleDB once ingestion has started.

## Core API Endpoints

### Stocks

```bash
curl http://localhost:8000/stocks
curl http://localhost:8000/stocks/AAPL/latest
curl "http://localhost:8000/stocks/AAPL?limit=100"
curl "http://localhost:8000/stocks/AAPL/stats"
```

### Analytics

```bash
curl http://localhost:8000/analytics/top-gainers
curl http://localhost:8000/analytics/top-losers
curl http://localhost:8000/analytics/volume-leaders
curl "http://localhost:8000/analytics/moving-average/AAPL?window=20"
curl "http://localhost:8000/analytics/volatility/AAPL"
```

### Alerts, Portfolio, Sentiment, Backtest

```bash
curl http://localhost:8000/alerts/history
curl http://localhost:8000/portfolio/positions
curl http://localhost:8000/sentiment/AAPL
curl http://localhost:8000/backtest/results
```

### WebSocket

```bash
wscat -c ws://localhost:8000/ws/stocks
```

## Environment Notes

Main backend variables are in `.env`:

1. `KAFKA_BOOTSTRAP_SERVERS`
2. `DATABASE_URL`
3. `REDIS_URL`
4. `POLYGON_API_KEY`
5. `NEWSAPI_KEY`
6. `ANTHROPIC_API_KEY`
7. `ALLOW_SIMULATED_DATA=false`

Dashboard variables are in `dashboard/.env`:

1. `VITE_API_URL`
2. `VITE_WS_URL`

## Monitoring

1. Prometheus config: `monitoring/prometheus.yml`
2. Grafana datasource provisioning: `monitoring/grafana/provisioning/datasources/prometheus.yml`
3. Grafana dashboard provisioning: `monitoring/grafana/provisioning/dashboards/dashboard.yml`
4. Dashboard JSON assets: `monitoring/grafana/dashboards`

## Useful Commands

```bash
make up
make seed
make logs
make down
```

```bash
cd dashboard
npm run build
npx playwright test
```

## Troubleshooting

1. If backend is up but no rows in `/stocks`, wait for ingestion loop and verify producer source credentials.
2. If Kafka topics are missing, run `make seed` again.
3. If auth calls fail, verify `JWT_SECRET_KEY` is set and backend restarted.
4. If dashboard cannot connect websocket, verify `VITE_WS_URL` and CORS/network reachability.

## Deployment

See `DEPLOY.md` for end-to-end deployment instructions for backend, dashboard, and post-deploy checks.
