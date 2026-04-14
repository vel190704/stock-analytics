import { cn } from '@/lib/utils';
import type { BacktestResult } from '@/types/stock';

function StatCard({ title, value, positive }: { title: string; value: string; positive: boolean }) {
  return (
    <div
      className={cn(
        'rounded-lg border p-3',
        positive ? 'border-gain/40 bg-gain/10' : 'border-loss/40 bg-loss/10',
      )}
    >
      <p className="font-mono text-xs uppercase tracking-wide text-text-muted">{title}</p>
      <p className={cn('mt-1 font-mono text-lg font-semibold', positive ? 'text-gain' : 'text-loss')}>
        {value}
      </p>
    </div>
  );
}

export function ResultStats({ result }: { result: BacktestResult | null }) {
  if (!result) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-lg border border-border bg-bg-secondary" />
        ))}
      </div>
    );
  }

  const benchmarkStart = result.equity_curve[0]?.benchmark_value ?? result.initial_capital;
  const benchmarkEnd = result.equity_curve[result.equity_curve.length - 1]?.benchmark_value ?? benchmarkStart;
  const benchmarkReturn = benchmarkStart ? ((benchmarkEnd - benchmarkStart) / benchmarkStart) * 100 : 0;
  const vsBenchmark = result.total_return_pct - benchmarkReturn;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <StatCard title="Total Return" value={`${result.total_return_pct.toFixed(2)}%`} positive={result.total_return_pct >= 0} />
      <StatCard title="Sharpe Ratio" value={result.sharpe_ratio.toFixed(2)} positive={result.sharpe_ratio >= 1} />
      <StatCard title="Max Drawdown" value={`${result.max_drawdown_pct.toFixed(2)}%`} positive={result.max_drawdown_pct >= -20} />
      <StatCard title="Win Rate" value={`${result.win_rate.toFixed(2)}%`} positive={result.win_rate >= 50} />
      <StatCard title="Total Trades" value={String(result.total_trades)} positive={result.total_trades > 0} />
      <StatCard title="vs Benchmark" value={`${vsBenchmark.toFixed(2)}%`} positive={vsBenchmark >= 0} />
    </div>
  );
}
