import { useNavigate } from 'react-router-dom';
import { useStockStore } from '@/store/stockStore';
import { useTopLosers } from '@/hooks/useStockData';
import { PriceChange } from '@/components/ui/PriceChange';
import { formatPrice, formatVolume } from '@/lib/utils';
import type { AnalyticsEntry } from '@/types/stock';

// ---------------------------------------------------------------------------
// Sparkline — same implementation as GainersTable
// ---------------------------------------------------------------------------

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <span className="text-text-muted">—</span>;

  const w = 60;
  const h = 24;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(' ');

  const last = values[values.length - 1];
  const first = values[0];
  const stroke = last >= first ? '#3fb950' : '#f85149';

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SkeletonRow({ rank }: { rank: number }) {
  return (
    <tr className="border-b border-border/50">
      <td className="px-3 py-2 text-xs text-text-muted">{rank}</td>
      <td className="px-3 py-2"><div className="h-3 w-12 animate-pulse rounded bg-bg-card" /></td>
      <td className="px-3 py-2"><div className="h-3 w-16 animate-pulse rounded bg-bg-card" /></td>
      <td className="px-3 py-2"><div className="h-5 w-16 animate-pulse rounded bg-bg-card" /></td>
      <td className="px-3 py-2"><div className="h-3 w-12 animate-pulse rounded bg-bg-card" /></td>
      <td className="px-3 py-2"><div className="h-6 w-[60px] animate-pulse rounded bg-bg-card" /></td>
    </tr>
  );
}

export function LosersTable() {
  const navigate = useNavigate();
  const setSelectedTicker = useStockStore((s) => s.setSelectedTicker);
  const latestPrices = useStockStore((s) => s.latestPrices);

  const { data: entries = [], isLoading } = useTopLosers();

  const priceHistory: Record<string, number[]> = Object.fromEntries(
    Object.entries(latestPrices).map(([ticker, summary]) => [
      ticker,
      [summary.latest_price],
    ]),
  );

  const handleRowClick = (ticker: string) => {
    setSelectedTicker(ticker);
    navigate(`/ticker/${ticker}`);
  };

  return (
    <div className="panel-surface flex flex-col overflow-hidden">
      <div className="border-b border-border/70 bg-gradient-to-r from-loss/10 to-transparent px-4 py-3">
        <h2 className="font-sans text-sm font-semibold text-text-primary">
          Top Losers
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px]">
          <thead>
            <tr className="border-b border-border/60">
              <th className="px-3 py-2 text-left font-mono text-xs text-text-muted">#</th>
              <th className="px-3 py-2 text-left font-mono text-xs text-text-muted">Ticker</th>
              <th className="px-3 py-2 text-right font-mono text-xs text-text-muted">Price</th>
              <th className="px-3 py-2 text-right font-mono text-xs text-text-muted">% Change</th>
              <th className="px-3 py-2 text-right font-mono text-xs text-text-muted">Volume</th>
              <th className="px-3 py-2 text-right font-mono text-xs text-text-muted">Trend</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }, (_, i) => <SkeletonRow key={i} rank={i + 1} />)
              : (entries as AnalyticsEntry[]).map((entry, idx) => (
                <tr
                  key={entry.ticker}
                  className="cursor-pointer border-b border-border/30 transition-colors hover:bg-bg-card/70"
                  onClick={() => handleRowClick(entry.ticker)}
                >
                  <td className="px-3 py-2 font-mono text-xs text-text-muted">{idx + 1}</td>
                  <td className="px-3 py-2 font-mono text-sm font-semibold text-text-primary">
                    {entry.ticker}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-text-primary">
                    {formatPrice(entry.close)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <PriceChange value={entry.pct_change} size="sm" />
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-text-muted">
                    {formatVolume(entry.volume)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Sparkline values={priceHistory[entry.ticker] ?? [entry.close]} />
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
