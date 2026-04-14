import { FormEvent, useState } from 'react';
import { useAddPosition, usePortfolioPositions, useTickerHistory } from '@/hooks/useStockData';
import { cn, formatPrice } from '@/lib/utils';

function Sparkline({ ticker }: { ticker: string }) {
  const { data } = useTickerHistory(ticker, '1m', 20);
  const rows = (Array.isArray(data) ? data : data?.data) ?? [];
  const values = rows
    .map((d) => Number(d.close))
    .filter((value) => Number.isFinite(value));

  if (values.length < 2) {
    return <span className="font-mono text-xs text-text-muted">-</span>;
  }

  const w = 80;
  const h = 22;
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

  const stroke = values[values.length - 1] >= values[0] ? '#3fb950' : '#f85149';

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline points={points} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}

export function PositionsTable() {
  const { data: positions = [], isLoading } = usePortfolioPositions();
  const addPosition = useAddPosition();

  const [open, setOpen] = useState(false);
  const [ticker, setTicker] = useState('AAPL');
  const [quantity, setQuantity] = useState('10');
  const [costBasis, setCostBasis] = useState('100');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await addPosition.mutateAsync({
      ticker,
      quantity: Number(quantity),
      cost_basis: Number(costBasis),
    });
    setOpen(false);
  };

  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-sans text-lg font-semibold text-text-primary">Positions</h3>
        <button
          onClick={() => setOpen(true)}
          className="rounded-md bg-accent px-3 py-2 font-mono text-xs font-semibold text-black"
        >
          Add Position
        </button>
      </div>

      {isLoading ? (
        <div className="h-40 animate-pulse rounded bg-bg-card" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1020px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Ticker</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Quantity</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Cost Basis</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Current Price</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Market Value</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">P&L</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">P&L%</th>
                <th className="px-2 py-2 text-right font-mono text-xs text-text-muted">Trend</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => {
                const quantity = Number(position.quantity ?? 0);
                const costBasis = Number(position.cost_basis ?? 0);
                const currentPrice = Number(position.current_price ?? 0);
                const marketValue = Number(position.market_value ?? 0);
                const unrealizedPnl = Number(position.unrealized_pnl ?? 0);
                const pnlPct = Number(position.pnl_pct ?? 0);

                return (
                  <tr
                    key={position.id}
                    className={cn(
                      'border-b border-border/40',
                      unrealizedPnl >= 0 ? 'bg-gain/5' : 'bg-loss/5',
                    )}
                  >
                    <td className="px-2 py-3 font-mono text-sm text-text-primary">{position.ticker}</td>
                    <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{quantity.toFixed(4)}</td>
                    <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{formatPrice(costBasis)}</td>
                    <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{formatPrice(currentPrice)}</td>
                    <td className="px-2 py-3 text-right font-mono text-xs text-text-primary">{formatPrice(marketValue)}</td>
                    <td className={cn('px-2 py-3 text-right font-mono text-xs', unrealizedPnl >= 0 ? 'text-gain' : 'text-loss')}>
                      {formatPrice(unrealizedPnl)}
                    </td>
                    <td className={cn('px-2 py-3 text-right font-mono text-xs', pnlPct >= 0 ? 'text-gain' : 'text-loss')}>
                      {pnlPct.toFixed(2)}%
                    </td>
                    <td className="px-2 py-3 text-right">
                      <Sparkline ticker={position.ticker} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4">
          <form onSubmit={onSubmit} className="w-full max-w-md rounded-lg border border-border bg-bg-secondary p-4">
            <h4 className="mb-3 font-sans text-lg font-semibold">Add Position</h4>
            <div className="space-y-3">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Ticker"
                className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
              />
              <input
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                type="number"
                step="0.0001"
                placeholder="Quantity"
                className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
              />
              <input
                value={costBasis}
                onChange={(e) => setCostBasis(e.target.value)}
                type="number"
                step="0.01"
                placeholder="Cost basis"
                className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded border border-border px-3 py-2 font-mono text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded bg-accent px-3 py-2 font-mono text-xs font-semibold text-black"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
