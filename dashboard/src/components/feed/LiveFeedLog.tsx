import { useCallback, useEffect, useRef, useState } from 'react';
import { format } from 'date-fns';
import { X } from 'lucide-react';
import { useStockStore } from '@/store/stockStore';
import { cn, formatPrice, formatPct, formatVolume, priceColour } from '@/lib/utils';
import type { LiveFeedEntry } from '@/types/stock';

// ---------------------------------------------------------------------------
// Single feed row
// ---------------------------------------------------------------------------

function FeedRow({ entry }: { entry: LiveFeedEntry }) {
  const colour = priceColour(entry.pct_change);
  const arrow = entry.pct_change > 0 ? '▲' : entry.pct_change < 0 ? '▼' : '—';
  const ts = format(new Date(entry.timestamp), 'HH:mm:ss.SSS');

  return (
    <div className="flex items-center gap-3 border-b border-border/20 px-3 py-1 font-mono text-xs animate-fade-in hover:bg-bg-card/50 transition-colors">
      {/* Timestamp */}
      <span className="shrink-0 text-text-muted">[{ts}]</span>

      {/* Ticker */}
      <span className="w-12 shrink-0 font-semibold text-text-primary">
        {entry.ticker}
      </span>

      {/* Price */}
      <span className="w-20 shrink-0 text-right text-text-primary">
        {formatPrice(entry.price)}
      </span>

      {/* Direction + % change */}
      <span className={cn('w-20 shrink-0 text-right', colour)}>
        {arrow} {formatPct(entry.pct_change)}
      </span>

      {/* Volume */}
      <span className="text-text-muted">
        vol: {formatVolume(entry.volume)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function LiveFeedLog() {
  const liveFeed = useStockStore((s) => s.liveFeed);
  const clearFeed = useStockStore((s) => s.clearFeed);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const isUserScrollingRef = useRef(false);

  // Auto-scroll to bottom when new entries arrive, unless user has scrolled up
  useEffect(() => {
    if (isPaused || isUserScrollingRef.current) return;
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [liveFeed, isPaused]);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const atBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 50;

    if (!atBottom) {
      setIsPaused(true);
    } else {
      setIsPaused(false);
    }
  }, []);

  const handleResume = useCallback(() => {
    setIsPaused(false);
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, []);

  return (
    <div className="flex flex-col rounded-lg border border-border bg-bg-secondary overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2">
          <h2 className="font-sans text-sm font-semibold text-text-primary">
            Live Feed
          </h2>
          <span className="rounded-full bg-accent/10 px-2 py-0.5 font-mono text-xs text-accent">
            {liveFeed.length} events
          </span>
          {isPaused && (
            <span className="rounded-full bg-amber/10 px-2 py-0.5 font-mono text-xs text-amber">
              Paused
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isPaused && (
            <button
              onClick={handleResume}
              className="rounded px-2 py-1 font-sans text-xs text-accent hover:bg-accent/10 transition-colors"
            >
              Resume ↓
            </button>
          )}
          <button
            onClick={clearFeed}
            className="flex items-center gap-1 rounded px-2 py-1 font-sans text-xs text-text-muted hover:bg-bg-card hover:text-text-primary transition-colors"
            title="Clear feed"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        </div>
      </div>

      {/* Scrollable log */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="h-[400px] overflow-y-auto"
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#30363d transparent' }}
      >
        {liveFeed.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <span className="font-mono text-xs text-text-muted">
              Waiting for live events…
            </span>
          </div>
        ) : (
          // Render newest at bottom — feed is (oldest → newest) already
          liveFeed.map((entry: LiveFeedEntry) => (
            <FeedRow key={entry.id} entry={entry} />
          ))
        )}
      </div>
    </div>
  );
}
