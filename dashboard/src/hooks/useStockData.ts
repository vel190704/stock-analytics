import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { subDays } from 'date-fns';
import { api } from '@/api/client';
import type { Interval } from '@/types/stock';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STALE_30S = 30_000;
const STALE_5S = 5_000;

// ---------------------------------------------------------------------------
// Stocks
// ---------------------------------------------------------------------------

/** All tickers with latest price — polled every 5 s. */
export function useTickerList() {
  return useQuery({
    queryKey: ['stocks', 'list'],
    queryFn: () => api.stocks.list(),
    staleTime: STALE_5S,
    refetchInterval: STALE_5S,
  });
}

/** OHLCV history for a single ticker. */
export function useTickerHistory(
  ticker: string,
  interval: Interval = '1m',
  limit = 200,
) {
  const end = new Date().toISOString();
  const start = subDays(new Date(), interval === '1d' ? 30 : 1).toISOString();

  return useQuery({
    queryKey: ['stocks', 'history', ticker, interval],
    queryFn: () =>
      api.stocks.history(ticker, { start, end, interval, limit }),
    staleTime: STALE_5S,
    refetchInterval: STALE_5S,
    enabled: !!ticker,
  });
}

/** Latest single event for a ticker. */
export function useTickerLatest(ticker: string) {
  return useQuery({
    queryKey: ['stocks', 'latest', ticker],
    queryFn: () => api.stocks.latest(ticker),
    staleTime: STALE_5S,
    refetchInterval: STALE_5S,
    enabled: !!ticker,
  });
}

/** Aggregated stats for a ticker. */
export function useTickerStats(
  ticker: string,
  start?: string,
  end?: string,
) {
  const defaultStart = subDays(new Date(), 1).toISOString();
  const defaultEnd = new Date().toISOString();

  return useQuery({
    queryKey: ['stocks', 'stats', ticker, start, end],
    queryFn: () =>
      api.stocks.stats(ticker, {
        start: start ?? defaultStart,
        end: end ?? defaultEnd,
      }),
    staleTime: STALE_30S,
    enabled: !!ticker,
  });
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

/** Top 10 gainers — refreshed every 30s. */
export function useTopGainers() {
  return useQuery({
    queryKey: ['analytics', 'top-gainers'],
    queryFn: () => api.analytics.topGainers(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

/** Top 10 losers — refreshed every 30s. */
export function useTopLosers() {
  return useQuery({
    queryKey: ['analytics', 'top-losers'],
    queryFn: () => api.analytics.topLosers(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

/** Volume leaders — refreshed every 30s. */
export function useVolumeLeaders() {
  return useQuery({
    queryKey: ['analytics', 'volume-leaders'],
    queryFn: () => api.analytics.volumeLeaders(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

/** Moving average for a ticker. */
export function useMovingAverage(ticker: string, window = 20) {
  return useQuery({
    queryKey: ['analytics', 'moving-average', ticker, window],
    queryFn: () => api.analytics.movingAverage(ticker, window),
    staleTime: STALE_30S,
    enabled: !!ticker,
  });
}

/** Volatility for a ticker. */
export function useVolatility(ticker: string) {
  return useQuery({
    queryKey: ['analytics', 'volatility', ticker],
    queryFn: () => api.analytics.volatility(ticker),
    staleTime: STALE_30S,
    enabled: !!ticker,
  });
}

/** Health check. */
export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health.check(),
    staleTime: 10_000,
    refetchInterval: 10_000,
    retry: false,
  });
}

export function useAlertRules() {
  return useQuery({
    queryKey: ['alerts', 'rules'],
    queryFn: () => api.alerts.listRules(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

export function useAlertHistory() {
  return useQuery({
    queryKey: ['alerts', 'history'],
    queryFn: () => api.alerts.history(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.alerts.createRule,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}

export function usePortfolioPositions() {
  return useQuery({
    queryKey: ['portfolio', 'positions'],
    queryFn: () => api.portfolio.listPositions(),
    staleTime: STALE_5S,
    refetchInterval: STALE_5S,
  });
}

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => api.portfolio.summary(),
    staleTime: STALE_5S,
    refetchInterval: STALE_5S,
  });
}

export function usePortfolioTrades(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['portfolio', 'trades', page, pageSize],
    queryFn: () => api.portfolio.tradeHistory(page, pageSize),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

export function useAddPosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.portfolio.addPosition,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useSentiment(ticker: string) {
  return useQuery({
    queryKey: ['sentiment', ticker],
    queryFn: () => api.sentiment.byTicker(ticker),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
    enabled: !!ticker,
  });
}

export function useSentimentAggregate(ticker: string) {
  return useQuery({
    queryKey: ['sentiment', ticker, 'aggregate'],
    queryFn: () => api.sentiment.aggregate(ticker),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
    enabled: !!ticker,
  });
}

export function useSentimentLeaderboard() {
  return useQuery({
    queryKey: ['sentiment', 'leaderboard'],
    queryFn: () => api.sentiment.leaderboard(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

export function useBacktestResults() {
  return useQuery({
    queryKey: ['backtest', 'results'],
    queryFn: () => api.backtest.recent(),
    staleTime: STALE_30S,
    refetchInterval: STALE_30S,
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.backtest.run,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['backtest'] });
    },
  });
}
