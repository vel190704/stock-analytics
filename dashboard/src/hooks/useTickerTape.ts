import { useMemo } from 'react';
import { useStockStore } from '@/store/stockStore';
import type { TickerSummary } from '@/types/stock';

/**
 * Derived hook that returns an ordered array of tickers for the scrolling tape.
 *
 * Tickers are sorted by absolute |pct_change| descending so the most active
 * names appear first in the tape. Falls back to alphabetical if all changes
 * are equal (e.g., at page load before WS data arrives).
 */
export function useTickerTape(): TickerSummary[] {
  const latestPrices = useStockStore((s) => s.latestPrices);

  return useMemo(() => {
    const entries = Object.values(latestPrices);

    if (entries.length === 0) return [];

    return [...entries].sort((a, b) => {
      const absDiff = Math.abs(b.pct_change) - Math.abs(a.pct_change);
      if (absDiff !== 0) return absDiff;
      return a.ticker.localeCompare(b.ticker);
    });
  }, [latestPrices]);
}
