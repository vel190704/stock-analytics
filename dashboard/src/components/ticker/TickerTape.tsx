import { useNavigate } from 'react-router-dom';
import { useTickerTape } from '@/hooks/useTickerTape';
import { useTickerList } from '@/hooks/useStockData';
import { useStockStore } from '@/store/stockStore';
import { cn, formatPrice, formatPct, priceColour } from '@/lib/utils';
import type { TickerSummary } from '@/types/stock';

// Each cell in the tape
function TapeCell({
  summary,
  onClick,
}: {
  summary: TickerSummary;
  onClick: () => void;
}) {
  const colour = priceColour(summary.pct_change);
  const arrow =
    summary.pct_change > 0 ? '▲' : summary.pct_change < 0 ? '▼' : '—';

  return (
    <button
      onClick={onClick}
      className="flex shrink-0 cursor-pointer items-center gap-2 border-r border-border/40 px-4 py-2 transition-colors hover:bg-bg-card"
      aria-label={`${summary.ticker} ${formatPrice(summary.latest_price)}`}
    >
      <span className="font-mono text-xs font-semibold text-text-primary">
        {summary.ticker}
      </span>
      <span className="font-mono text-xs text-text-primary">
        {formatPrice(summary.latest_price)}
      </span>
      <span className={cn('font-mono text-xs font-medium', colour)}>
        {arrow} {formatPct(summary.pct_change)}
      </span>
    </button>
  );
}

/**
 * Horizontally scrolling price strip pinned between the topbar and content.
 *
 * Implementation:
 * - Two identical copies of the ticker list concatenated → seamless CSS loop
 * - `animation-play-state: paused` on hover to freeze scroll
 * - Derives data from Zustand `latestPrices` (updated via WebSocket)
 * - Falls back to REST poll via `useTickerList` on initial load
 */
export function TickerTape() {
  const navigate = useNavigate();
  const setSelectedTicker = useStockStore((s) => s.setSelectedTicker);
  const tapeTickers = useTickerTape();

  // Populate Zustand cache on mount via REST poll (WS may not have arrived yet)
  useTickerList();

  const handleClick = (ticker: string) => {
    setSelectedTicker(ticker);
    navigate(`/ticker/${ticker}`);
  };

  // Need at least 1 entry to render the tape
  if (tapeTickers.length === 0) {
    return (
      <div className="ticker-tape h-9 flex items-center border-b border-border bg-bg-secondary px-4">
        <span className="font-mono text-xs text-text-muted animate-pulse">
          Waiting for market data…
        </span>
      </div>
    );
  }

  // Duplicate items → seamless infinite scroll without JS
  const doubled = [...tapeTickers, ...tapeTickers];

  return (
    <div className="ticker-tape h-9 overflow-hidden border-b border-border bg-bg-secondary">
      <div
        className="group flex h-full items-center"
        style={{ width: 'max-content' }}
      >
        {/*
         * Single track: doubled list so when the first copy scrolls out
         * the second copy is already filling in — no gap.
         *
         * `animate-ticker-scroll` is defined in tailwind.config.ts with
         * `animation-play-state: running` by default; the `group-hover:`
         * variant pauses it.
         */}
        <div
          className="flex animate-ticker-scroll group-hover:[animation-play-state:paused]"
          style={{ willChange: 'transform' }}
        >
          {doubled.map((summary, idx) => (
            <TapeCell
              key={`${summary.ticker}-${idx}`}
              summary={summary}
              onClick={() => handleClick(summary.ticker)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
