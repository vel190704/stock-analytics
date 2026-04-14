import { useMemo, useState } from 'react';
import { BacktestConfig } from '@/components/backtest/BacktestConfig';
import { EquityCurveChart } from '@/components/backtest/EquityCurveChart';
import { ResultStats } from '@/components/backtest/ResultStats';
import { useBacktestResults, useRunBacktest } from '@/hooks/useStockData';
import type { BacktestResult } from '@/types/stock';

export function BacktestPage() {
  const { data: recent = [] } = useBacktestResults();
  const runBacktest = useRunBacktest();
  const [result, setResult] = useState<BacktestResult | null>(null);

  const activeResult = result ?? recent[0] ?? null;

  const run = async (payload: {
    ticker: string;
    strategy: 'ma_crossover' | 'rsi_oversold' | 'breakout';
    params: Record<string, number>;
    start_date: string;
    end_date: string;
    initial_capital: number;
  }) => {
    const data = await runBacktest.mutateAsync(payload);
    setResult(data);
  };

  const tradeLog = useMemo(() => activeResult?.trades ?? [], [activeResult]);

  return (
    <div className="flex flex-col gap-4">
      <BacktestConfig isRunning={runBacktest.isPending} onRun={run} />
      <ResultStats result={activeResult} />
      <EquityCurveChart result={activeResult} />

      <div className="panel-surface p-4">
        <h3 className="mb-3 font-sans text-lg font-semibold">Trade Log</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-border/70">
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Date</th>
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Action</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Price</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Shares</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Value</th>
              </tr>
            </thead>
            <tbody>
              {tradeLog.map((trade, idx) => (
                <tr key={`${trade.date}-${idx}`} className="border-b border-border/30 transition-colors hover:bg-bg-card/45">
                  <td className="px-2 py-3 font-mono text-xs text-text-muted">
                    {new Date(trade.date).toLocaleString()}
                  </td>
                  <td className="px-2 py-3">
                    <span
                      className={`rounded-full px-2 py-1 font-mono text-[10px] ${trade.action === 'BUY' ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss'
                        }`}
                    >
                      {trade.action}
                    </span>
                  </td>
                  <td className="px-2 py-3 text-right font-mono text-xs">${trade.price.toFixed(2)}</td>
                  <td className="px-2 py-3 text-right font-mono text-xs">{trade.shares.toFixed(4)}</td>
                  <td className="px-2 py-3 text-right font-mono text-xs">${trade.value.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
