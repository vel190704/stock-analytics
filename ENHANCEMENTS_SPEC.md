# ENHANCEMENTS_SPEC.md
# Stock Market Analytics Pipeline — Phase 2 Enhancements

You are a senior full-stack engineer extending an existing production-grade stock
analytics pipeline. The existing stack is:
- Backend: FastAPI + Kafka (confluent-kafka) + TimescaleDB + Redis + Prometheus
- Frontend: React 18 + TypeScript + Zustand + TanStack Query + Recharts
- All files live in ~/project/stock_market/ (backend) and ~/project/stock_market/dashboard/ (frontend)

Do NOT regenerate existing files. Only generate the new files listed below.
No placeholder logic. No TODO comments. Every file must be complete and runnable.

---

## Enhancement 1 — AI-Powered Price Alert Engine

### What it does
Uses the Anthropic Claude API to analyse incoming price data and detect
anomalies (sudden spikes, unusual volume, breakouts). Sends email alerts.
This is the most impressive resume differentiator — it adds an AI/ML angle.

### New backend files

**src/services/alert_service.py**
- Pydantic model: AlertRule (ticker, condition: above/below/pct_change_exceeds, threshold, user_email)
- Store alert rules in Redis hash: alerts:{ticker}
- On each processed StockEvent, check rules for that ticker
- If triggered: call Claude API with a structured prompt to generate a human-readable
  alert summary explaining WHY the alert fired and what the price action suggests
- Send email via smtplib (HTML template)
- Log alert to a new alerts table in TimescaleDB

**src/database/models.py** — ADD these models (don't replace existing):
```python
class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    condition: Mapped[str] = mapped_column(String(30))  # above/below/pct_change_exceeds
    threshold: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    user_email: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

class AlertFired(Base):
    __tablename__ = "alerts_fired"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id"))
    triggered_price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    ai_summary: Mapped[str] = mapped_column(Text)
    fired_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

**src/api/routes/alerts.py**
```
POST /alerts/rules           → create alert rule
GET  /alerts/rules           → list all rules
DELETE /alerts/rules/{id}    → delete rule
GET  /alerts/history         → last 50 fired alerts with AI summaries
GET  /alerts/history/{ticker} → fired alerts for specific ticker
```

**Claude API integration (src/services/claude_service.py)**
```python
import anthropic

async def analyse_price_event(ticker: str, event: StockEvent, rule: AlertRule) -> str:
    """Call Claude to generate a natural language alert summary."""
    client = anthropic.AsyncAnthropic()
    prompt = f"""
    Stock alert triggered for {ticker}.
    Rule: price {rule.condition} ${rule.threshold}
    Current price: ${event.close}
    Price change: {event.pct_change:.2f}%
    Volume: {event.volume:,}
    VWAP: ${event.vwap}

    In 2-3 sentences, explain what this price action suggests to a retail investor.
    Be specific about the magnitude and context. Do not give financial advice.
    """
    message = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
```

### New frontend files (dashboard/src/)

**components/alerts/AlertsPanel.tsx**
- Form to create alert rules: ticker dropdown, condition select, threshold input, email
- Table showing last 10 fired alerts with AI-generated summaries
- Each alert row has a coloured badge: ABOVE/BELOW/SPIKE
- AI summary text in a muted blockquote style
- TanStack Query with 30s refresh

**Add to sidebar navigation**: "Alerts" link → /alerts page

---

## Enhancement 2 — Portfolio Tracker

### What it does
Lets users track a personal stock portfolio: add positions (ticker, quantity, cost_basis),
see real-time P&L against live prices, and view trade history.

### New backend files

**src/database/models.py** — ADD:
```python
class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(4))   # BUY / SELL
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4),
        generatedAlwaysAs=text("quantity * price"), persisted=True)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

**src/api/routes/portfolio.py**
```
POST   /portfolio/positions       → add position
GET    /portfolio/positions       → list positions with live P&L
DELETE /portfolio/positions/{id}  → close position
POST   /portfolio/trades          → record a trade
GET    /portfolio/trades          → trade history (paginated)
GET    /portfolio/summary         → total value, total P&L, best/worst position
```

**src/services/portfolio_service.py**
- `get_positions_with_pnl()` — joins positions with latest price from Redis
  to compute: market_value, unrealized_pnl, pnl_pct per position
- `get_portfolio_summary()` — aggregate P&L, total_invested, total_value, daily_change
- Cache portfolio summary in Redis TTL=5s

### New frontend files

**pages/PortfolioPage.tsx** — layout:
```
┌────────────────────────────────────────────────┐
│  Summary cards: Total Value | P&L | Daily Change│
├──────────────────┬─────────────────────────────┤
│  Positions table │  Portfolio value chart       │
│  (with live P&L) │  (Recharts AreaChart)        │
├──────────────────┴─────────────────────────────┤
│  Trade history table                           │
└────────────────────────────────────────────────┘
```

**components/portfolio/PositionsTable.tsx**
- Columns: Ticker | Quantity | Cost Basis | Current Price | Market Value | P&L | P&L%
- Positive P&L = green background tint; negative = red tint
- Refresh every 5s (live prices update P&L in real time)
- "Add Position" button opens modal (shadcn/ui Dialog)
- Sparkline column showing last 20 prices

**components/portfolio/PortfolioChart.tsx**
- Recharts AreaChart of portfolio total value over time
- Gradient fill: green above starting value, red below
- Tooltip shows exact value + % change from starting value

---

## Enhancement 3 — Sentiment Analysis Feed

### What it does
Scrapes financial news headlines for tracked tickers using NewsAPI (free tier),
sends batches to Claude for sentiment scoring, stores results, and shows
a sentiment timeline alongside price charts.

### New backend files

**src/services/sentiment_service.py**
```python
import anthropic
from datetime import datetime, timedelta

async def fetch_and_score_sentiment(ticker: str) -> list[SentimentScore]:
    """Fetch news headlines and score sentiment via Claude."""
    # 1. Fetch from NewsAPI: GET https://newsapi.org/v2/everything
    #    params: q=ticker, from=yesterday, sortBy=publishedAt, pageSize=10
    # 2. Build prompt with all 10 headlines
    # 3. Call Claude once for batch scoring (efficient, single API call)
    client = anthropic.AsyncAnthropic()
    prompt = f"""
    Score the sentiment of these {ticker} news headlines.
    For each headline, respond with a JSON array of objects:
    {{"headline": "...", "score": 0.85, "label": "bullish|bearish|neutral", "reason": "..."}}
    score is 0.0 (very bearish) to 1.0 (very bullish). 0.5 is neutral.
    Respond ONLY with valid JSON. No preamble.

    Headlines:
    {headlines_text}
    """
    message = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_sentiment_response(message.content[0].text)
```

**src/database/models.py** — ADD:
```python
class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    headline: Mapped[str] = mapped_column(Text)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # 0.0000 to 1.0000
    label: Mapped[str] = mapped_column(String(10))         # bullish/bearish/neutral
    reason: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500))
    scored_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    # TimescaleDB hypertable on scored_at
```

**src/api/routes/sentiment.py**
```
GET /sentiment/{ticker}                  → last 20 scored headlines with scores
GET /sentiment/{ticker}/aggregate        → avg score last 24h, 7d, 30d
GET /sentiment/leaderboard               → all tickers ranked by sentiment score
POST /sentiment/{ticker}/refresh         → trigger fresh news fetch + scoring
```

**Background task**: APScheduler job running every 30min → fetch + score all tracked tickers

### New frontend files

**components/sentiment/SentimentGauge.tsx**
- Semicircular gauge SVG (0=bearish, 100=bullish, needle at current score)
- Color gradient: red at 0, amber at 50, green at 100
- Shows: score value, label (Bullish/Bearish/Neutral), last updated time

**components/sentiment/SentimentTimeline.tsx**
- Recharts LineChart of sentiment score over time
- Overlaid on top of price chart in TickerDetailPage (dual Y-axis)
- Tooltip shows: price, sentiment score, top headline at that timestamp

**components/sentiment/SentimentFeed.tsx**
- Scrollable list of recent headlines with coloured score badges
- Bullish = green, Bearish = red, Neutral = gray
- Click headline → opens source URL in new tab
- Shows "Powered by Claude AI" attribution badge

---

## Enhancement 4 — Backtesting Engine

### What it does
Users define a simple trading strategy (moving average crossover, RSI threshold,
breakout), run it against historical TimescaleDB data, and see performance metrics
with a chart comparing strategy vs buy-and-hold.

### New backend files

**src/services/backtest_service.py**
```python
from dataclasses import dataclass
from typing import Callable

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
    trades: list[dict]         # [{date, action, price, shares, value}]
    equity_curve: list[dict]   # [{date, value, benchmark_value}]

async def run_backtest(
    ticker: str,
    strategy: str,        # "ma_crossover" | "rsi_oversold" | "breakout"
    params: dict,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 10000.0,
) -> BacktestResult:
    """
    Fetch OHLCV history from TimescaleDB.
    Apply strategy logic to generate BUY/SELL signals.
    Simulate trades with no slippage, 0.1% commission per trade.
    Calculate: Sharpe ratio (annualised), max drawdown, win rate.
    Compare equity curve vs buy-and-hold benchmark.
    """
```

**Strategies to implement**:
- `ma_crossover`: params={fast_window: 10, slow_window: 20} — BUY when fast MA crosses above slow MA
- `rsi_oversold`: params={rsi_period: 14, oversold: 30, overbought: 70} — BUY below oversold, SELL above overbought
- `breakout`: params={lookback: 20} — BUY when close > max(high, lookback days)

**src/api/routes/backtest.py**
```
POST /backtest/run            → run backtest, return full BacktestResult
GET  /backtest/results        → list past backtests (last 10, stored in Redis)
```

### New frontend files

**pages/BacktestPage.tsx** — layout:
```
┌──────────────────────────────────────────────────────┐
│  Config panel: ticker, strategy, params, date range  │
├──────────────────────────────────────────────────────┤
│  Results: stat cards (return, Sharpe, drawdown, etc) │
├──────────────────────────────────────────────────────┤
│  Equity curve chart (strategy vs buy-and-hold)       │
├──────────────────────────────────────────────────────┤
│  Trade log table                                     │
└──────────────────────────────────────────────────────┘
```

**components/backtest/BacktestConfig.tsx**
- Ticker select (from tracked tickers list)
- Strategy dropdown: MA Crossover | RSI Oversold | Breakout
- Dynamic params panel: shows correct inputs for selected strategy
- Date range picker (start / end)
- Initial capital input
- Run button with loading spinner

**components/backtest/EquityCurveChart.tsx**
- Recharts ComposedChart with two lines:
  - Strategy equity curve (blue)
  - Buy-and-hold benchmark (gray dashed)
- Shaded area: green when strategy above benchmark, red below
- Annotations at each trade: tiny BUY (▲ green) and SELL (▼ red) markers
- Tooltip: date, strategy value, benchmark value, difference

**components/backtest/ResultStats.tsx**
- 6 stat cards in a grid:
  Total Return | Sharpe Ratio | Max Drawdown | Win Rate | Total Trades | vs Benchmark
- Color coding: green if positive/above benchmark, red if not

---

## Enhancement 5 — Infrastructure & Polish

### GitHub Actions CI/CD (.github/workflows/ci.yml)
```yaml
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env: { POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
      kafka:
        image: confluentinc/cp-kafka:7.6.0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd dashboard && npm ci && npm run build && npm run test

  docker-build:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker/docker-compose.yml build
```

### JWT Authentication (src/api/auth.py)
Minimal auth layer — don't over-engineer it, just protect write endpoints:
- POST /auth/register → email + password → returns JWT
- POST /auth/login → email + password → returns JWT
- Dependency: `get_current_user` — FastAPI dependency that validates Bearer token
- Apply `Depends(get_current_user)` to: POST /alerts/rules, POST /portfolio/positions,
  POST /portfolio/trades, POST /backtest/run
- Use python-jose for JWT, passlib for bcrypt hashing

### Rate Limiting (src/api/middleware.py)
- Add slowapi middleware to FastAPI app
- Limits: 60 requests/minute per IP for GET endpoints
- 10 requests/minute per IP for POST endpoints
- 429 response with Retry-After header

### Swagger UI improvements (src/main.py)
Update FastAPI app creation:
```python
app = FastAPI(
    title="Stock Analytics API",
    description="Real-time stock market analytics with AI-powered alerts and sentiment analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "stocks", "description": "OHLCV data and analytics"},
        {"name": "analytics", "description": "Top gainers, losers, volume"},
        {"name": "alerts", "description": "AI-powered price alerts"},
        {"name": "portfolio", "description": "Portfolio tracking and P&L"},
        {"name": "sentiment", "description": "Claude AI sentiment scoring"},
        {"name": "backtest", "description": "Strategy backtesting engine"},
        {"name": "system", "description": "Health checks and metrics"},
    ],
)
```

### WebSocket rooms per ticker
Modify src/api/websocket.py to support topic rooms:
- WS /ws/stocks → broadcasts all events (existing behaviour, keep it)
- WS /ws/stocks/{ticker} → broadcasts only events for that ticker
- Use a ConnectionManager with a dict: {ticker: set[WebSocket]}
- On connect to /ws/stocks/{ticker}, add to that ticker's room only
- This reduces bandwidth for TickerDetailPage which only needs 1 ticker

### New frontend: Alerts page (dashboard/src/pages/AlertsPage.tsx)
Full page at /alerts:
- Left panel: create alert form
  - Ticker select (populated from /stocks)
  - Condition: Price Above / Price Below / % Change Exceeds
  - Threshold: number input
  - Email: input
  - Submit button
- Right panel: alerts history table
  - Columns: Ticker | Condition | Triggered Price | AI Summary | Time
  - AI Summary column: truncated to 2 lines, expand on click
  - Status badge: FIRED (red) / ACTIVE (green)
  - Refresh every 30s

### Playwright E2E tests (dashboard/e2e/)
```typescript
// e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test'

test('dashboard loads and shows ticker tape', async ({ page }) => {
  await page.goto('http://localhost:3001')
  await expect(page.locator('.ticker-tape')).toBeVisible()
})

test('gainers table shows at least 3 rows', async ({ page }) => {
  await page.goto('http://localhost:3001')
  const rows = page.locator('[data-testid="gainers-row"]')
  await expect(rows).toHaveCountGreaterThan(2)
})

test('clicking ticker navigates to detail page', async ({ page }) => {
  await page.goto('http://localhost:3001')
  await page.click('[data-testid="ticker-AAPL"]')
  await expect(page).toHaveURL(/\/ticker\/AAPL/)
  await expect(page.locator('[data-testid="candlestick-chart"]')).toBeVisible()
})

test('portfolio page shows P&L', async ({ page }) => {
  await page.goto('http://localhost:3001/portfolio')
  await expect(page.locator('[data-testid="portfolio-summary"]')).toBeVisible()
})

test('alerts page creates and shows alert', async ({ page }) => {
  await page.goto('http://localhost:3001/alerts')
  await page.selectOption('[data-testid="alert-ticker"]', 'AAPL')
  await page.fill('[data-testid="alert-threshold"]', '200')
  await page.fill('[data-testid="alert-email"]', 'test@example.com')
  await page.click('[data-testid="create-alert-btn"]')
  await expect(page.locator('[data-testid="alerts-table"]')).toBeVisible()
})
```

### Updated .env.example
```env
# Existing
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/stockdb
REDIS_URL=redis://localhost:6379
POLYGON_API_KEY=

# New in Phase 2
ANTHROPIC_API_KEY=           # Get from console.anthropic.com
NEWSAPI_KEY=                 # Get free key at newsapi.org
JWT_SECRET_KEY=              # Generate: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=               # Gmail app password
ALERT_EMAIL_FROM=alerts@stockanalytics.local

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Updated pyproject.toml dependencies (ADD these to existing)
```toml
# AI
"anthropic>=0.25.0",
# Auth
"python-jose[cryptography]>=3.3.0",
"passlib[bcrypt]>=1.7.4",
# Rate limiting
"slowapi>=0.1.9",
# Scheduling
"apscheduler>=3.10.0",
# HTTP client for news
"httpx>=0.27.0",   # already in deps
# News API
"newsapi-python>=0.2.7",
```

---

## Generation order (follow exactly)

### Backend additions
1. `src/services/claude_service.py`
2. `src/services/sentiment_service.py`
3. `src/services/alert_service.py`
4. `src/services/portfolio_service.py`
5. `src/services/backtest_service.py`
6. Update `src/database/models.py` — add new models ONLY (append, don't replace)
7. `src/api/routes/alerts.py`
8. `src/api/routes/portfolio.py`
9. `src/api/routes/sentiment.py`
10. `src/api/routes/backtest.py`
11. `src/api/auth.py`
12. `src/api/middleware.py`
13. Update `src/main.py` — add new routers + middleware (don't regenerate existing)
14. New Alembic migration: `migrations/versions/0002_phase2_tables.py`
15. `.github/workflows/ci.yml`
16. Update `pyproject.toml` — add new deps only

### Frontend additions
17. `dashboard/src/types/stock.ts` — ADD new interfaces (AlertRule, AlertFired,
    Position, Trade, SentimentScore, BacktestResult) — don't regenerate existing
18. `dashboard/src/api/client.ts` — ADD new API functions for alerts, portfolio,
    sentiment, backtest — don't regenerate existing
19. `dashboard/src/hooks/useStockData.ts` — ADD new query hooks — don't replace
20. `dashboard/src/components/alerts/AlertsPanel.tsx`
21. `dashboard/src/components/portfolio/PositionsTable.tsx`
22. `dashboard/src/components/portfolio/PortfolioChart.tsx`
23. `dashboard/src/components/sentiment/SentimentGauge.tsx`
24. `dashboard/src/components/sentiment/SentimentTimeline.tsx`
25. `dashboard/src/components/sentiment/SentimentFeed.tsx`
26. `dashboard/src/components/backtest/BacktestConfig.tsx`
27. `dashboard/src/components/backtest/EquityCurveChart.tsx`
28. `dashboard/src/components/backtest/ResultStats.tsx`
29. `dashboard/src/pages/AlertsPage.tsx`
30. `dashboard/src/pages/PortfolioPage.tsx`
31. `dashboard/src/pages/SentimentPage.tsx`
32. `dashboard/src/pages/BacktestPage.tsx`
33. Update `dashboard/src/App.tsx` — add new routes only
34. Update `dashboard/src/components/layout/Sidebar.tsx` — add new nav links
35. `dashboard/e2e/dashboard.spec.ts`
36. `dashboard/playwright.config.ts`
37. Update `dashboard/package.json` — add playwright dep

Generate each file completely. No truncation. No `# ... rest of code`.

---

## Resume impact of each enhancement

| Enhancement | Skills demonstrated | Interview talking points |
|---|---|---|
| AI Alerts (Claude API) | LLM integration, async API calls, event-driven AI | "I used Claude to generate human-readable explanations of price anomalies, not just raw alerts" |
| Portfolio Tracker | Relational data, real-time P&L, complex queries | "Positions join against Redis for sub-second P&L updates without hitting Postgres" |
| Sentiment Analysis | NLP, batch API calls, background scheduling | "Single Claude API call scores 10 headlines at once — cost-efficient batch design" |
| Backtesting Engine | Financial algorithms, Sharpe ratio, statistical metrics | "Sharpe ratio and max drawdown calculated directly from TimescaleDB time-series queries" |
| CI/CD + Auth + E2E | Production engineering practices | "GitHub Actions runs backend pytest with real testcontainers and frontend Playwright on every PR" |

---

**After Copilot generates all 37 files, your quick-start:**

```bash
# Backend
cd ~/project/stock_market
pip install -e ".[dev]"
alembic upgrade head        # runs migration 0002
make up                     # starts all Docker services

# Frontend
cd dashboard
npm install
npm run dev

# Run E2E tests
npx playwright install
npx playwright test
```

The Claude API (Anthropic) key is the single most impactful addition — it transforms this from a "data pipeline project" into an "AI-powered trading platform", which is a completely different tier on a resume.
