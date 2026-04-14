import { format } from 'date-fns';
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';
import { useTickerHistory } from '@/hooks/useStockData';
import { useStockStore } from '@/store/stockStore';
import { formatVolume } from '@/lib/utils';
import type { Interval, StockEvent } from '@/types/stock';

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

function VolumeTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0]?.payload as StockEvent | undefined;
  if (!d) return null;

  return (
    <div className="rounded border border-border bg-bg-card p-2 text-xs font-mono shadow-xl">
      <p className="text-text-muted">
        {format(new Date(d.event_time), 'MMM dd HH:mm')}
      </p>
      <p className="text-text-primary">Vol: {formatVolume(d.volume)}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface VolumeChartProps {
  ticker: string;
  interval?: Interval;
}

export function VolumeChart({ ticker, interval }: VolumeChartProps) {
  const selectedInterval = useStockStore((s) => s.selectedInterval);
  const effectiveInterval = interval ?? selectedInterval;

  const { data: historyResp, isLoading } = useTickerHistory(
    ticker,
    effectiveInterval,
  );

  const events: StockEvent[] = (Array.isArray(historyResp) ? historyResp : historyResp?.data) ?? [];
  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
  );
  const dedupedEvents = Array.from(
    new Map(sortedEvents.map((event) => [event.event_time, event])).values(),
  );
  const visibleEvents = dedupedEvents.slice(-90);

  if (isLoading) {
    return (
      <div className="flex h-24 items-center justify-center">
        <span className="animate-pulse font-mono text-xs text-text-muted">
          Loading volume…
        </span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={80}>
      <BarChart
        data={visibleEvents}
        margin={{ top: 0, right: 8, left: 0, bottom: 0 }}
      >
        <XAxis
          dataKey="event_time"
          tickFormatter={(v: string) => format(new Date(v), 'HH:mm')}
          tick={{ fill: '#7d8590', fontSize: 9, fontFamily: 'JetBrains Mono' }}
          axisLine={{ stroke: '#30363d' }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tickFormatter={(v: number) => formatVolume(v)}
          tick={{ fill: '#7d8590', fontSize: 9, fontFamily: 'JetBrains Mono' }}
          axisLine={false}
          tickLine={false}
          width={48}
        />
        <Tooltip content={<VolumeTooltip />} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="volume" maxBarSize={12} radius={[2, 2, 0, 0]}>
          {visibleEvents.map((entry, index) => (
            <Cell
              key={`vol-${index}`}
              fill={entry.close >= entry.open ? '#3fb950' : '#f85149'}
              fillOpacity={0.7}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
