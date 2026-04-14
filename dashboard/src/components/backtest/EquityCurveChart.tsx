import { ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, Area, Scatter } from 'recharts';
import type { BacktestResult } from '@/types/stock';

function buildTradeMarkers(result: BacktestResult) {
  const byDate = new Map(
    result.equity_curve.map((point) => [point.date, { ...point, value: Number(point.value) }]),
  );
  return result.trades
    .map((trade) => {
      const point = byDate.get(trade.date);
      if (!point) return null;
      return {
        date: trade.date,
        value: point.value,
        action: trade.action,
      };
    })
    .filter((item): item is { date: string; value: number; action: 'BUY' | 'SELL' } => !!item);
}

export function EquityCurveChart({ result }: { result: BacktestResult | null }) {
  if (!result || result.equity_curve.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center rounded-lg border border-border bg-bg-secondary">
        <span className="font-mono text-xs text-text-muted">Run a backtest to see the equity curve</span>
      </div>
    );
  }

  const chartData = result.equity_curve.map((point) => {
    const strategyValue = Number(point.value);
    const benchmarkValue = Number(point.benchmark_value);
    const delta = strategyValue - benchmarkValue;
    return {
      ...point,
      value: strategyValue,
      benchmark_value: benchmarkValue,
      above: delta > 0 ? strategyValue : null,
      below: delta <= 0 ? strategyValue : null,
    };
  });

  const trades = buildTradeMarkers(result);

  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <h3 className="mb-3 font-sans text-lg font-semibold">Equity Curve vs Benchmark</h3>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData}>
          <defs>
            <linearGradient id="eqAbove" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3fb950" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#3fb950" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="eqBelow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f85149" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#f85149" stopOpacity={0.05} />
            </linearGradient>
          </defs>

          <XAxis dataKey="date" tick={{ fill: '#7d8590', fontSize: 10 }} />
          <YAxis tick={{ fill: '#7d8590', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
            formatter={(value: number, name: string) => {
              if (name === 'value') return [`$${value.toFixed(2)}`, 'Strategy'];
              if (name === 'benchmark_value') return [`$${value.toFixed(2)}`, 'Benchmark'];
              return [value, name];
            }}
            labelFormatter={(_, payload) => {
              const p = payload?.[0]?.payload;
              if (!p) return '';
              const diff = p.value - p.benchmark_value;
              const sign = diff >= 0 ? '+' : '';
              return `${p.date} | Diff ${sign}$${diff.toFixed(2)}`;
            }}
          />

          <Area type="monotone" dataKey="above" stroke="none" fill="url(#eqAbove)" connectNulls />
          <Area type="monotone" dataKey="below" stroke="none" fill="url(#eqBelow)" connectNulls />
          <Line type="monotone" dataKey="value" stroke="#58a6ff" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="benchmark_value" stroke="#8b949e" dot={false} strokeWidth={2} strokeDasharray="6 4" />

          <Scatter
            data={trades.map((t) => ({ ...t, marker: t.action === 'BUY' ? '▲' : '▼' }))}
            dataKey="value"
            shape={(props: unknown) => {
              const { cx, cy, payload } = props as { cx: number; cy: number; payload: { action: 'BUY' | 'SELL' } };
              return (
                <text x={cx} y={cy} textAnchor="middle" fill={payload.action === 'BUY' ? '#3fb950' : '#f85149'} fontSize={10}>
                  {payload.action === 'BUY' ? '▲' : '▼'}
                </text>
              );
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
