import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { subDays } from 'date-fns';
import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { VolumeChart } from '@/components/charts/VolumeChart';
import { PriceChange } from '@/components/ui/PriceChange';
import { StatCard } from '@/components/ui/StatCard';
import { useTickerLatest, useTickerStats, useVolatility } from '@/hooks/useStockData';
import { formatPrice, formatVolume } from '@/lib/utils';

/**
 * Detail page for a single ticker.
 *
 * Route: /ticker/:symbol
 *
 * Layout:
 *   [← Back | TICKER  $price  ▲▼ %]
 *   [Stats row: Min | Max | Avg | Volume | Events]
 *   [Candlestick + Volume charts]
 *   [Volatility stat card]
 */
export function TickerDetailPage() {
  const { symbol = '' } = useParams<{ symbol: string }>();
  const navigate = useNavigate();

  const ticker = symbol.trim().toUpperCase();

  const { data: latest, isLoading: latestLoading } = useTickerLatest(ticker);
  const { data: stats, isLoading: statsLoading } = useTickerStats(
    ticker,
    subDays(new Date(), 1).toISOString(),
    new Date().toISOString(),
  );
  const { data: volatilityData } = useVolatility(ticker);

  const minPrice = Number(stats?.min_price ?? 0);
  const maxPrice = Number(stats?.max_price ?? 0);
  const avgPrice = Number(stats?.avg_price ?? 0);
  const totalVolume = Number(stats?.total_volume ?? 0);
  const eventCount = Number(stats?.event_count ?? 0);
  const latestClose = Number(latest?.close ?? 0);
  const latestPct = Number(latest?.pct_change ?? 0);

  return (
    <div className="flex flex-col gap-6">
      {/* Header row */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 font-sans text-sm text-text-muted transition-colors hover:bg-bg-card hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        <div className="flex items-center gap-3">
          <h1 className="font-mono text-2xl font-bold text-text-primary">
            {ticker}
          </h1>

          {latestLoading ? (
            <div className="h-7 w-24 animate-pulse rounded bg-bg-card" />
          ) : latest ? (
            <>
              <span className="font-mono text-2xl font-semibold text-text-primary">
                {formatPrice(latestClose)}
              </span>
              <PriceChange value={latestPct} size="lg" />
            </>
          ) : null}
        </div>

        {latest?.exchange && (
          <span className="rounded border border-border px-2 py-0.5 font-mono text-xs text-text-muted">
            {latest.exchange}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
        <StatCard
          title="Min Price"
          value={statsLoading ? '…' : formatPrice(minPrice)}
        />
        <StatCard
          title="Max Price"
          value={statsLoading ? '…' : formatPrice(maxPrice)}
        />
        <StatCard
          title="Avg Price"
          value={statsLoading ? '…' : formatPrice(avgPrice)}
        />
        <StatCard
          title="Total Volume"
          value={statsLoading ? '…' : formatVolume(totalVolume)}
        />
        <StatCard
          title="Events (24h)"
          value={statsLoading ? '…' : eventCount.toLocaleString()}
        />
      </div>

      {/* Charts */}
      <div className="panel-surface p-4">
        <CandlestickChart ticker={ticker} showMA maWindow={20} />
        <div className="mt-2 border-t border-border/70 pt-2">
          <p className="mb-1 font-mono text-xs text-text-muted">Volume</p>
          <VolumeChart ticker={ticker} />
        </div>
      </div>

      {/* Volatility */}
      {volatilityData && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <StatCard
            title="Volatility (Std Dev)"
            value={
              volatilityData.volatility != null
                ? `$${Number(volatilityData.volatility).toFixed(4)}`
                : 'N/A'
            }
            subValue={`Based on ${volatilityData.sample_size} samples`}
          />
          <StatCard
            title="Source"
            value={latest?.source ?? '—'}
            subValue={latest ? `Last update: ${new Date(latest.event_time).toLocaleTimeString()}` : undefined}
          />
        </div>
      )}

      {!latestLoading && !latest && (
        <div className="panel-surface p-4 text-sm text-text-muted">
          No latest quote found for {ticker}. Verify the ticker exists and that live ingestion is running.
        </div>
      )}
    </div>
  );
}
