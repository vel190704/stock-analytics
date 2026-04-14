import { useStockStore } from '@/store/stockStore';
import { GainersTable } from '@/components/tables/GainersTable';
import { LosersTable } from '@/components/tables/LosersTable';
import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { VolumeChart } from '@/components/charts/VolumeChart';
import { LiveFeedLog } from '@/components/feed/LiveFeedLog';
import { PriceChange } from '@/components/ui/PriceChange';
import { useTickerLatest } from '@/hooks/useStockData';
import { formatPrice } from '@/lib/utils';

/**
 * Main dashboard page.
 *
 * Grid layout:
 *   [Gainers (40%)]  [Candlestick + Volume (60%)]
 *   [Losers  (40%)]  [                           ]
 *   [Live Feed — full width                      ]
 *
 * Below 1024px: stacks to single column.
 */
export function DashboardPage() {
  const selectedTicker = useStockStore((s) => s.selectedTicker);
  const wsStatus = useStockStore((s) => s.wsStatus);
  const { data: latestTicker, isLoading: latestLoading } = useTickerLatest(selectedTicker);

  const wsTone =
    wsStatus === 'connected'
      ? 'bg-gain/15 text-gain border-gain/30'
      : wsStatus === 'connecting'
        ? 'bg-amber/15 text-amber border-amber/30'
        : 'bg-loss/15 text-loss border-loss/30';

  return (
    <div className="stagger-in flex flex-col gap-4 lg:gap-5">
      <section className="panel-surface relative overflow-hidden p-5 lg:p-6">
        <div className="pointer-events-none absolute right-0 top-0 h-44 w-44 rounded-full bg-accent/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-10 -left-8 h-40 w-40 rounded-full bg-gain/15 blur-3xl" />

        <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-text-muted">
              Live market pulse
            </p>
            <div className="mt-2 flex flex-wrap items-end gap-3">
              <h1 className="font-sans text-3xl font-semibold leading-none text-text-primary lg:text-4xl">
                {selectedTicker}
              </h1>
              {latestLoading ? (
                <span className="h-7 w-24 animate-pulse rounded bg-bg-card" />
              ) : (
                <span className="font-mono text-2xl text-text-primary">
                  {formatPrice(Number(latestTicker?.close ?? 0))}
                </span>
              )}
              {!latestLoading && <PriceChange value={Number(latestTicker?.pct_change ?? 0)} size="md" />}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wide ${wsTone}`}>
              {wsStatus}
            </span>
            <span className="rounded-full border border-border/70 bg-bg-card/50 px-3 py-1 font-mono text-[11px] uppercase tracking-wide text-text-muted">
              Stream: ws/stocks
            </span>
          </div>
        </div>
      </section>

      {/* Charts + Tables row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_3fr]">
        {/* Left column: Gainers + Losers */}
        <div className="flex flex-col gap-4">
          <GainersTable />
          <LosersTable />
        </div>

        {/* Right column: Candlestick + Volume */}
        <div className="panel-surface flex flex-col gap-2 p-4">
          <CandlestickChart ticker={selectedTicker} showMA />
          <div className="border-t border-border/70 pt-2">
            <p className="mb-1 font-mono text-xs text-text-muted">Volume</p>
            <VolumeChart ticker={selectedTicker} />
          </div>
        </div>
      </div>

      {/* Full-width live feed */}
      <LiveFeedLog />
    </div>
  );
}
