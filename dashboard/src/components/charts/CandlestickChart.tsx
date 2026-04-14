import { useCallback, useState } from 'react';
import { format } from 'date-fns';
import {
  ComposedChart,
  Line,
  Rectangle,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';
import { useStockStore } from '@/store/stockStore';
import { useMovingAverage, useTickerHistory } from '@/hooks/useStockData';
import { formatPrice, formatVolume } from '@/lib/utils';
import type { Interval, StockEvent } from '@/types/stock';

// ---------------------------------------------------------------------------
// Custom candlestick shape
// ---------------------------------------------------------------------------

interface CandlePayload extends StockEvent {
  [key: string]: unknown;
}

function CandlestickBar(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: CandlePayload;
  [key: string]: unknown;
}) {
  const { x = 0, y = 0, width = 0, payload } = props;
  if (!payload) return null;

  const { open, close, high, low } = payload;
  const isUp = close >= open;
  const fill = isUp ? '#3fb950' : '#f85149';
  const stroke = fill;

  // Body bounds
  const bodyTop = Math.min(open, close);
  const bodyBottom = Math.max(open, close);
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1);

  // Map price → pixel y (recharts passes y as the pixel position of the bar)
  // We rely on the YAxis scale being passed implicitly through the data range.
  // Since recharts passes the pixel y coordinates, we need to use the scale.
  // The simplest way: use the Rectangle and rely on recharts' layout.
  const candleX = x + width * 0.1;
  const candleWidth = width * 0.8;
  const wickX = x + width / 2;

  // These pixel values come from recharts scaling via the YAxis
  const yScale = props.yScale as ((v: number) => number) | undefined;
  if (!yScale) return null;

  const highY = yScale(high);
  const lowY = yScale(low);
  const openY = yScale(open);
  const closeY = yScale(close);
  const bodyTopY = Math.min(openY, closeY);
  const bodyBottomY = Math.max(openY, closeY);
  const bodyH = Math.max(bodyBottomY - bodyTopY, 1);

  return (
    <g>
      {/* Upper wick */}
      <line
        x1={wickX}
        y1={highY}
        x2={wickX}
        y2={bodyTopY}
        stroke={stroke}
        strokeWidth={1}
      />
      {/* Body */}
      <Rectangle
        x={candleX}
        y={bodyTopY}
        width={candleWidth}
        height={bodyH}
        fill={fill}
        stroke={stroke}
      />
      {/* Lower wick */}
      <line
        x1={wickX}
        y1={bodyBottomY}
        x2={wickX}
        y2={lowY}
        stroke={stroke}
        strokeWidth={1}
      />
    </g>
  );
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

function CandleTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0]?.payload as StockEvent | undefined;
  if (!d) return null;

  return (
    <div className="rounded border border-border bg-bg-card p-3 text-xs font-mono shadow-xl">
      <p className="mb-1 text-text-muted">
        {format(new Date(d.event_time), 'MMM dd HH:mm')}
      </p>
      <p className="text-text-primary">O: {formatPrice(d.open)}</p>
      <p className="text-text-primary">H: {formatPrice(d.high)}</p>
      <p className="text-text-primary">L: {formatPrice(d.low)}</p>
      <p className="text-text-primary">C: {formatPrice(d.close)}</p>
      <p className="text-text-muted">V: {formatVolume(d.volume)}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Interval selector
// ---------------------------------------------------------------------------

const INTERVALS: Interval[] = ['1m', '5m', '1h', '1d'];

function IntervalTabs({
  selected,
  onChange,
}: {
  selected: Interval;
  onChange: (i: Interval) => void;
}) {
  return (
    <div className="flex gap-1">
      {INTERVALS.map((i) => (
        <button
          key={i}
          onClick={() => onChange(i)}
          className={`rounded px-2.5 py-1 font-mono text-xs font-medium transition-colors ${selected === i
              ? 'bg-accent/20 text-accent'
              : 'text-text-muted hover:bg-bg-card hover:text-text-primary'
            }`}
        >
          {i}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface CandlestickChartProps {
  ticker: string;
  showMA?: boolean;
  maWindow?: number;
}

type MovingAveragePoint = {
  event_time: string;
  ma?: number | null;
  moving_average?: number | null;
};

type MovingAverageResponse =
  | MovingAveragePoint[]
  | {
      values?: MovingAveragePoint[];
    }
  | null
  | undefined;

function normalizeMovingAverage(
  response: MovingAverageResponse,
): Array<[string, number]> {
  const points = Array.isArray(response)
    ? response
    : Array.isArray(response?.values)
      ? response.values
      : [];

  return points
    .map((point) => {
      const value = point.ma ?? point.moving_average;
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        return null;
      }
      return [point.event_time, value] as [string, number];
    })
    .filter((item): item is [string, number] => item !== null);
}

export function CandlestickChart({
  ticker,
  showMA = true,
  maWindow = 20,
}: CandlestickChartProps) {
  const setSelectedInterval = useStockStore((s) => s.setSelectedInterval);
  const selectedInterval = useStockStore((s) => s.selectedInterval);

  const [localInterval, setLocalInterval] = useState<Interval>(selectedInterval);

  const handleIntervalChange = useCallback(
    (interval: Interval) => {
      setLocalInterval(interval);
      setSelectedInterval(interval);
    },
    [setSelectedInterval],
  );

  const { data: historyResp, isLoading } = useTickerHistory(
    ticker,
    localInterval,
  );
  const { data: maData } = useMovingAverage(ticker, maWindow);

  const events: StockEvent[] = (Array.isArray(historyResp) ? historyResp : historyResp?.data) ?? [];

  // Build an MA lookup keyed by event_time
  const maLookup = new Map<string, number>(
    normalizeMovingAverage(maData as MovingAverageResponse),
  );

  // Merge MA values into the event list
  const chartData = events.map((e) => ({
    ...e,
    ma: maLookup.get(e.event_time) ?? null,
  }));

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-bg-card">
        <span className="animate-pulse font-mono text-xs text-text-muted">
          Loading chart…
        </span>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-bg-card">
        <span className="font-mono text-xs text-text-muted">
          No data for {ticker}
        </span>
      </div>
    );
  }

  // Compute price domain with 1% padding
  const prices = events.flatMap((e) => [e.high, e.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const pad = (maxPrice - minPrice) * 0.01;
  const domain: [number, number] = [minPrice - pad, maxPrice + pad];

  return (
    <div data-testid="candlestick-chart" className="flex flex-col gap-2">
      {/* Header row */}
      <div className="flex items-center justify-between px-1">
        <span className="font-mono text-sm font-semibold text-text-primary">
          {ticker}
        </span>
        <IntervalTabs
          selected={localInterval}
          onChange={handleIntervalChange}
        />
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart
          data={chartData}
          margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
        >
          <XAxis
            dataKey="event_time"
            tickFormatter={(v: string) => format(new Date(v), 'HH:mm')}
            tick={{ fill: '#7d8590', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: '#30363d' }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            domain={domain}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            tick={{ fill: '#7d8590', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip content={<CandleTooltip />} />

          {/* Candlestick bars — rendered as a custom shape on the close dataKey */}
          {chartData.map((d, i) => {
            const isUp = d.close >= d.open;
            const fill = isUp ? '#3fb950' : '#f85149';
            return null; // We'll use the Bar shape below
          })}

          {/* Moving average overlay */}
          {showMA && (
            <Line
              type="monotone"
              dataKey="ma"
              stroke="#d29922"
              strokeWidth={1.5}
              dot={false}
              name={`MA(${maWindow})`}
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Recharts doesn't natively support candlestick — render via SVG overlay */}
      <CandlestickOverlay data={chartData} ticker={ticker} domain={domain} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pure SVG candlestick overlay (rendered on top of RechaRts axes)
// ---------------------------------------------------------------------------

interface OverlayBar {
  event_time: string;
  open: number;
  close: number;
  high: number;
  low: number;
}

function CandlestickOverlay({
  data,
  domain,
}: {
  data: OverlayBar[];
  ticker: string;
  domain: [number, number];
}) {
  const HEIGHT = 300;
  const MARGIN_LEFT = 56;
  const MARGIN_RIGHT = 8;
  const MARGIN_TOP = 4;
  const MARGIN_BOTTOM = 20;

  const chartH = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM;

  const priceToY = useCallback(
    (price: number) => {
      const [minP, maxP] = domain;
      const ratio = (maxP - price) / (maxP - minP);
      return MARGIN_TOP + ratio * chartH;
    },
    [domain, chartH],
  );

  if (data.length === 0) return null;

  return (
    <div className="pointer-events-none relative -mt-[320px] h-[300px]">
      <svg
        width="100%"
        height={HEIGHT}
        style={{ position: 'absolute', top: 0, left: 0 }}
        viewBox={`0 0 800 ${HEIGHT}`}
        preserveAspectRatio="none"
      >
        {data.map((d, i) => {
          const totalWidth = 800 - MARGIN_LEFT - MARGIN_RIGHT;
          const bandW = totalWidth / data.length;
          const centerX = MARGIN_LEFT + (i + 0.5) * bandW;
          const candleW = Math.max(bandW * 0.6, 2);

          const highY = priceToY(d.high);
          const lowY = priceToY(d.low);
          const openY = priceToY(d.open);
          const closeY = priceToY(d.close);

          const bodyTop = Math.min(openY, closeY);
          const bodyH = Math.max(Math.abs(closeY - openY), 1);
          const isUp = d.close >= d.open;
          const colour = isUp ? '#3fb950' : '#f85149';

          return (
            <g key={`${d.event_time}-${i}`}>
              {/* Upper wick */}
              <line
                x1={centerX}
                y1={highY}
                x2={centerX}
                y2={bodyTop}
                stroke={colour}
                strokeWidth={1}
              />
              {/* Candle body */}
              <rect
                x={centerX - candleW / 2}
                y={bodyTop}
                width={candleW}
                height={bodyH}
                fill={colour}
              />
              {/* Lower wick */}
              <line
                x1={centerX}
                y1={bodyTop + bodyH}
                x2={centerX}
                y2={lowY}
                stroke={colour}
                strokeWidth={1}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
