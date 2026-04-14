// ---------------------------------------------------------------------------
// Core domain types
// ---------------------------------------------------------------------------

export interface StockEvent {
  id: number;
  ticker: string;
  exchange: string;
  event_time: string; // ISO 8601 UTC
  ingested_at: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  vwap: number | null;
  price_change: number;
  pct_change: number;
  source: string;
}

export interface TickerSummary {
  ticker: string;
  latest_price: number;
  pct_change: number;
  price_change: number;
  volume: number;
  event_time: string;
}

export interface OHLCVBar {
  bucket: string; // ISO 8601 bucket start
  ticker: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}

export interface AnalyticsEntry {
  ticker: string;
  pct_change: number;
  price_change: number;
  close: number;
  volume: number;
}

export interface TickerStats {
  ticker: string;
  min_price: number;
  max_price: number;
  avg_price: number;
  total_volume: number;
  event_count: number;
  start: string;
  end: string;
}

export interface MovingAverage {
  ticker: string;
  window: number;
  values: { event_time: string; ma: number }[];
}

export interface LiveFeedEntry {
  id: string; // uuid generated client-side
  ticker: string;
  price: number;
  pct_change: number;
  volume: number;
  timestamp: string;
}

export type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export type Interval = '1m' | '5m' | '1h' | '1d';

// ---------------------------------------------------------------------------
// API response wrappers
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthStatus {
  status: string;
  checks: {
    kafka: boolean;
    postgres: boolean;
    redis: boolean;
  };
}

export interface VolatilityResult {
  ticker: string;
  volatility: number | null;
  sample_size: number;
}

export interface AlertRule {
  id: number;
  ticker: string;
  condition: 'above' | 'below' | 'pct_change_exceeds';
  threshold: number;
  user_email: string;
  is_active: boolean;
  created_at: string;
}

export interface AlertFired {
  id: number;
  ticker: string;
  rule_id: number;
  condition: 'above' | 'below' | 'pct_change_exceeds';
  triggered_price: number;
  ai_summary: string;
  fired_at: string;
}

export interface Position {
  id: number;
  ticker: string;
  quantity: number;
  cost_basis: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_pct: number;
  daily_change: number;
  opened_at: string;
}

export interface Trade {
  id: number;
  ticker: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  total: number;
  executed_at: string;
}

export interface SentimentScore {
  id: number;
  ticker: string;
  headline: string;
  score: number;
  label: 'bullish' | 'bearish' | 'neutral';
  reason: string;
  source_url: string;
  scored_at: string;
}

export interface BacktestTrade {
  date: string;
  action: 'BUY' | 'SELL';
  price: number;
  shares: number;
  value: number;
}

export interface EquityPoint {
  date: string;
  value: number;
  benchmark_value: number;
}

export interface BacktestResult {
  ticker: string;
  strategy: 'ma_crossover' | 'rsi_oversold' | 'breakout';
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_value: number;
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate: number;
  total_trades: number;
  trades: BacktestTrade[];
  equity_curve: EquityPoint[];
}
