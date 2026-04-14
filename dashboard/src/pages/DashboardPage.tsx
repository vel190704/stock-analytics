import { useStockStore } from '@/store/stockStore';
import { GainersTable } from '@/components/tables/GainersTable';
import { LosersTable } from '@/components/tables/LosersTable';
import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { VolumeChart } from '@/components/charts/VolumeChart';
import { LiveFeedLog } from '@/components/feed/LiveFeedLog';

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

  return (
    <div className="flex flex-col gap-4">
      {/* Charts + Tables row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_3fr]">
        {/* Left column: Gainers + Losers */}
        <div className="flex flex-col gap-4">
          <GainersTable />
          <LosersTable />
        </div>

        {/* Right column: Candlestick + Volume */}
        <div className="flex flex-col gap-2 rounded-lg border border-border bg-bg-secondary p-4">
          <CandlestickChart ticker={selectedTicker} showMA />
          <div className="border-t border-border pt-2">
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
