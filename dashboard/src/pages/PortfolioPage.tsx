import { useMemo } from 'react';
import { PortfolioChart } from '@/components/portfolio/PortfolioChart';
import { PositionsTable } from '@/components/portfolio/PositionsTable';
import { usePortfolioSummary, usePortfolioTrades } from '@/hooks/useStockData';
import { formatPrice } from '@/lib/utils';

function SummaryCard({ title, value, tone = 'neutral' }: { title: string; value: string; tone?: 'gain' | 'loss' | 'neutral' }) {
  const toneClass = tone === 'gain' ? 'text-gain' : tone === 'loss' ? 'text-loss' : 'text-text-primary';
  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <p className="font-mono text-xs uppercase tracking-wide text-text-muted">{title}</p>
      <p className={`mt-1 font-mono text-xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

export function PortfolioPage() {
  const { data: summary } = usePortfolioSummary();
  const { data: tradesResp } = usePortfolioTrades(1, 100);

  const chartData = useMemo(() => {
    const rows = tradesResp?.data ?? [];
    if (!rows.length) {
      return [];
    }

    let running = 0;
    return [...rows]
      .reverse()
      .map((trade) => {
        running += trade.action === 'BUY' ? trade.total : -trade.total;
        return {
          time: new Date(trade.executed_at).toLocaleDateString(),
          value: Math.abs(running),
        };
      });
  }, [tradesResp]);

  return (
    <div className="flex flex-col gap-4">
      <div data-testid="portfolio-summary" className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <SummaryCard title="Total Value" value={formatPrice(summary?.total_value)} />
        <SummaryCard
          title="Total P&L"
          value={formatPrice(summary?.total_pnl)}
          tone={(summary?.total_pnl ?? 0) >= 0 ? 'gain' : 'loss'}
        />
        <SummaryCard
          title="Daily Change"
          value={formatPrice(summary?.daily_change)}
          tone={(summary?.daily_change ?? 0) >= 0 ? 'gain' : 'loss'}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
        <PositionsTable />
        <PortfolioChart data={chartData} />
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-4">
        <h3 className="mb-3 font-sans text-lg font-semibold">Trade History</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Time</th>
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Ticker</th>
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Action</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Quantity</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Price</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Total</th>
              </tr>
            </thead>
            <tbody>
              {(tradesResp?.data ?? []).map((trade) => (
                <tr key={trade.id} className="border-b border-border/40">
                  <td className="px-2 py-3 font-mono text-xs text-text-muted">
                    {new Date(trade.executed_at).toLocaleString()}
                  </td>
                  <td className="px-2 py-3 font-mono text-sm text-text-primary">{trade.ticker}</td>
                  <td className="px-2 py-3">
                    <span
                      className={`rounded-full px-2 py-1 font-mono text-[10px] ${trade.action === 'BUY' ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss'
                        }`}
                    >
                      {trade.action}
                    </span>
                  </td>
                  <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{trade.quantity.toFixed(4)}</td>
                  <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{formatPrice(trade.price)}</td>
                  <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{formatPrice(trade.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
