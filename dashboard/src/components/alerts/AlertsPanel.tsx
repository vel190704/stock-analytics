import { FormEvent, useMemo, useState } from 'react';
import { useAlertHistory, useCreateAlertRule, useTickerList } from '@/hooks/useStockData';
import { formatPrice } from '@/lib/utils';

const CONDITIONS = [
  { value: 'above', label: 'Price Above' },
  { value: 'below', label: 'Price Below' },
  { value: 'pct_change_exceeds', label: '% Change Exceeds' },
] as const;

function badgeClass(condition: string): string {
  if (condition === 'above') return 'bg-emerald-500/20 text-emerald-300';
  if (condition === 'below') return 'bg-rose-500/20 text-rose-300';
  return 'bg-amber-500/20 text-amber-300';
}

function badgeLabel(condition: string): string {
  if (condition === 'above') return 'ABOVE';
  if (condition === 'below') return 'BELOW';
  return 'SPIKE';
}

export function AlertsPanel() {
  const { data: tickersResp } = useTickerList();
  const { data: history = [], isLoading: historyLoading } = useAlertHistory();
  const createRule = useCreateAlertRule();

  const tickers = useMemo(
    () => (tickersResp?.data ?? []).map((item) => item.ticker),
    [tickersResp],
  );

  const [ticker, setTicker] = useState('AAPL');
  const [condition, setCondition] = useState<'above' | 'below' | 'pct_change_exceeds'>('above');
  const [threshold, setThreshold] = useState('200');
  const [email, setEmail] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    await createRule.mutateAsync({
      ticker,
      condition,
      threshold: Number(threshold),
      user_email: email,
    });

    setThreshold('');
  };

  const rows = history.slice(0, 10);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_1fr]">
      <form
        onSubmit={onSubmit}
        className="rounded-lg border border-border bg-bg-secondary p-4"
      >
        <h2 className="mb-4 font-sans text-lg font-semibold text-text-primary">Create Alert Rule</h2>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Ticker</label>
            <select
              data-testid="alert-ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary"
            >
              {tickers.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Condition</label>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value as 'above' | 'below' | 'pct_change_exceeds')}
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary"
            >
              {CONDITIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Threshold</label>
            <input
              data-testid="alert-threshold"
              type="number"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary"
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Email</label>
            <input
              data-testid="alert-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary"
              placeholder="you@example.com"
            />
          </div>

          <button
            data-testid="create-alert-btn"
            type="submit"
            disabled={createRule.isPending}
            className="w-full rounded-md bg-accent px-4 py-2 text-sm font-semibold text-black transition-opacity disabled:opacity-70"
          >
            {createRule.isPending ? 'Creating…' : 'Create Alert'}
          </button>
        </div>
      </form>

      <div className="rounded-lg border border-border bg-bg-secondary p-4">
        <h2 className="mb-3 font-sans text-lg font-semibold text-text-primary">Latest Fired Alerts</h2>

        {historyLoading ? (
          <div className="h-40 animate-pulse rounded bg-bg-card" />
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="alerts-table" className="w-full min-w-[760px] border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Ticker</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Condition</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Price</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">AI Summary</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Time</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id} className="border-b border-border/40 align-top">
                    <td className="px-2 py-3 font-mono text-sm text-text-primary">{item.ticker}</td>
                    <td className="px-2 py-3">
                      <span
                        className={`rounded-full px-2 py-1 font-mono text-[10px] uppercase ${badgeClass(item.condition)}`}
                      >
                        {badgeLabel(item.condition)}
                      </span>
                    </td>
                    <td className="px-2 py-3 font-mono text-sm text-text-primary">
                      {formatPrice(item.triggered_price)}
                    </td>
                    <td className="px-2 py-3 text-sm text-text-primary">
                      <blockquote className="rounded border-l-2 border-border bg-bg-card px-3 py-2 text-text-muted">
                        {item.ai_summary}
                      </blockquote>
                    </td>
                    <td className="px-2 py-3 font-mono text-xs text-text-muted">
                      {new Date(item.fired_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
