import axios, { type AxiosInstance } from 'axios';
import type {
  AlertFired,
  AlertRule,
  AnalyticsEntry,
  BacktestResult,
  HealthStatus,
  PaginatedResponse,
  Position,
  SentimentScore,
  StockEvent,
  Trade,
  TickerStats,
  TickerSummary,
  VolatilityResult,
} from '@/types/stock';

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const AUTH_STORAGE_KEY = 'stock_jwt';

function normalizeBaseURL(raw: string | undefined): string {
  if (!raw || raw.trim().length === 0) {
    return 'http://localhost:8000';
  }
  return raw.replace(/\/$/, '');
}

const baseURL = normalizeBaseURL(import.meta.env.VITE_API_URL);

const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 10_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function setAuthToken(token: string | null) {
  if (!token) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_STORAGE_KEY);
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

http.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthToken();
    }
    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// Generic GET helper (fully typed)
// ---------------------------------------------------------------------------

async function GET<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const { data } = await http.get<T>(path, { params });
  return data;
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  auth: {
    register: (email: string, password: string): Promise<{ access_token: string; token_type: string }> =>
      http
        .post('/auth/register', { email, password })
        .then((res) => res.data),
    login: (email: string, password: string): Promise<{ access_token: string; token_type: string }> =>
      http
        .post('/auth/login', { email, password })
        .then((res) => res.data),
  },

  stocks: {
    /** Returns latest price snapshot for every known ticker. */
    list: (): Promise<PaginatedResponse<TickerSummary>> =>
      GET<PaginatedResponse<TickerSummary>>('/stocks'),

    /**
     * OHLCV history for a single ticker.
     * @param ticker  Symbol, e.g. "AAPL"
     * @param params  Query params: start, end (ISO 8601), interval, limit
     */
    history: (
      ticker: string,
      params?: {
        start?: string;
        end?: string;
        interval?: string;
        limit?: number;
      },
    ): Promise<PaginatedResponse<StockEvent>> =>
      GET<PaginatedResponse<StockEvent>>(`/stocks/${ticker}`, params),

    /** Most recent event for a ticker. */
    latest: (ticker: string): Promise<StockEvent> =>
      GET<StockEvent>(`/stocks/${ticker}/latest`),

    /** Aggregated stats for a ticker over a date range. */
    stats: (
      ticker: string,
      params?: { start?: string; end?: string },
    ): Promise<TickerStats> =>
      GET<TickerStats>(`/stocks/${ticker}/stats`, params),
  },

  analytics: {
    /** Top 10 tickers by % gain today. */
    topGainers: (): Promise<AnalyticsEntry[]> =>
      GET<PaginatedResponse<AnalyticsEntry>>('/analytics/top-gainers').then((r) => r.data),

    /** Bottom 10 tickers by % change today. */
    topLosers: (): Promise<AnalyticsEntry[]> =>
      GET<PaginatedResponse<AnalyticsEntry>>('/analytics/top-losers').then((r) => r.data),

    /** Top 10 tickers by total volume today. */
    volumeLeaders: (): Promise<AnalyticsEntry[]> =>
      GET<PaginatedResponse<AnalyticsEntry>>('/analytics/volume-leaders').then((r) => r.data),

    /** Rolling N-period SMA for a ticker. */
    movingAverage: (
      ticker: string,
      window: number,
    ): Promise<Array<{ event_time: string; close: number; moving_average: number | null }>> =>
      GET(`/analytics/moving-average/${ticker}`, { window }),

    /** Rolling volatility (std dev of close prices). */
    volatility: (ticker: string): Promise<VolatilityResult> =>
      GET<VolatilityResult>(`/analytics/volatility/${ticker}`),
  },

  health: {
    check: (): Promise<HealthStatus> => GET<HealthStatus>('/health'),
  },

  alerts: {
    createRule: (payload: {
      ticker: string;
      condition: 'above' | 'below' | 'pct_change_exceeds';
      threshold: number;
      user_email: string;
    }): Promise<AlertRule> => http.post('/alerts/rules', payload).then((res) => res.data),
    listRules: (): Promise<AlertRule[]> => GET<AlertRule[]>('/alerts/rules'),
    deleteRule: (id: number): Promise<void> => http.delete(`/alerts/rules/${id}`).then(() => undefined),
    history: (): Promise<AlertFired[]> => GET<AlertFired[]>('/alerts/history'),
    historyByTicker: (ticker: string): Promise<AlertFired[]> => GET<AlertFired[]>(`/alerts/history/${ticker}`),
  },

  portfolio: {
    addPosition: (payload: { ticker: string; quantity: number; cost_basis: number }): Promise<Position> =>
      http.post('/portfolio/positions', payload).then((res) => res.data),
    listPositions: (): Promise<Position[]> => GET<Position[]>('/portfolio/positions'),
    closePosition: (id: number): Promise<void> => http.delete(`/portfolio/positions/${id}`).then(() => undefined),
    recordTrade: (payload: { ticker: string; action: 'BUY' | 'SELL'; quantity: number; price: number }): Promise<Trade> =>
      http.post('/portfolio/trades', payload).then((res) => res.data),
    tradeHistory: (
      page = 1,
      pageSize = 20,
    ): Promise<{ total: number; page: number; page_size: number; data: Trade[] }> =>
      GET('/portfolio/trades', { page, page_size: pageSize }),
    summary: (): Promise<{
      total_positions: number;
      total_invested: number;
      total_value: number;
      total_pnl: number;
      daily_change: number;
      best_position: Position | null;
      worst_position: Position | null;
    }> => GET('/portfolio/summary'),
  },

  sentiment: {
    byTicker: (ticker: string): Promise<SentimentScore[]> => GET<SentimentScore[]>(`/sentiment/${ticker}`),
    aggregate: (ticker: string): Promise<{ ticker: string; avg_24h: number | null; avg_7d: number | null; avg_30d: number | null }> =>
      GET(`/sentiment/${ticker}/aggregate`),
    leaderboard: (): Promise<{ ticker: string; avg_score: number; sample_size: number }[]> =>
      GET('/sentiment/leaderboard'),
    refresh: (ticker: string): Promise<{ ticker: string; inserted: number }> =>
      http.post(`/sentiment/${ticker}/refresh`).then((res) => res.data),
  },

  backtest: {
    run: (payload: {
      ticker: string;
      strategy: 'ma_crossover' | 'rsi_oversold' | 'breakout';
      params: Record<string, number>;
      start_date: string;
      end_date: string;
      initial_capital: number;
    }): Promise<BacktestResult> => http.post('/backtest/run', payload).then((res) => res.data),
    recent: (): Promise<BacktestResult[]> => GET('/backtest/results'),
  },
};
