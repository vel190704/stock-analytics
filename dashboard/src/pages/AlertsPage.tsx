import { FormEvent, useMemo, useState } from 'react';
import { useAlertHistory, useCreateAlertRule, useTickerList } from '@/hooks/useStockData';
import { formatPrice } from '@/lib/utils';

export function AlertsPage() {
  const { data: tickersResp } = useTickerList();
  const { data: history = [], isLoading } = useAlertHistory();
  const createRule = useCreateAlertRule();

  const tickers = useMemo(() => (tickersResp?.data ?? []).map((t) => t.ticker), [tickersResp]);

  const [ticker, setTicker] = useState('AAPL');
  const [condition, setCondition] = useState<'above' | 'below' | 'pct_change_exceeds'>('above');
  const [threshold, setThreshold] = useState('200');
  const [email, setEmail] = useState('');
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    await createRule.mutateAsync({
      ticker,
      condition,
      threshold: Number(threshold),
      user_email: email,
    });
  };

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_1fr]">
      <form onSubmit={submit} className="rounded-lg border border-border bg-bg-secondary p-4">
        <h1 className="mb-4 font-sans text-2xl font-semibold text-text-primary">Alerts</h1>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Ticker</label>
            <select
              data-testid="alert-ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
            >
              {tickers.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Condition</label>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value as 'above' | 'below' | 'pct_change_exceeds')}
              className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
            >
              <option value="above">Price Above</option>
              <option value="below">Price Below</option>
              <option value="pct_change_exceeds">% Change Exceeds</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Threshold</label>
            <input
              data-testid="alert-threshold"
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Email</label>
            <input
              data-testid="alert-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
            />
          </div>

          <button
            data-testid="create-alert-btn"
            disabled={createRule.isPending}
            className="w-full rounded bg-accent px-4 py-2 font-mono text-xs font-semibold text-black disabled:opacity-70"
          >
            {createRule.isPending ? 'Submitting…' : 'Create Alert'}
          </button>
        </div>
      </form>

      <div className="rounded-lg border border-border bg-bg-secondary p-4">
        <h2 className="mb-3 font-sans text-lg font-semibold">Alert History</h2>

        {isLoading ? (
          <div className="h-48 animate-pulse rounded bg-bg-card" />
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="alerts-table" className="w-full min-w-[900px] border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Ticker</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Condition</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Triggered Price</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">AI Summary</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Status</th>
                  <th className="px-2 py-2 text-left font-mono text-xs text-text-muted">Time</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => {
                  const open = expanded[item.id];
                  const conditionLabel =
                    item.condition === 'above'
                      ? 'Price Above'
                      : item.condition === 'below'
                        ? 'Price Below'
                        : '% Change Exceeds';
                  return (
                    <tr key={item.id} className="border-b border-border/40 align-top">
                      <td className="px-2 py-3 font-mono text-sm">{item.ticker}</td>
                      <td className="px-2 py-3 font-mono text-xs text-text-muted">{conditionLabel}</td>
                      <td className="px-2 py-3 font-mono text-xs">{formatPrice(item.triggered_price)}</td>
                      <td className="px-2 py-3 text-sm text-text-primary">
                        <button
                          type="button"
                          onClick={() => setExpanded((prev) => ({ ...prev, [item.id]: !prev[item.id] }))}
                          className="max-w-[420px] text-left"
                        >
                          <span className={open ? '' : 'line-clamp-2'}>{item.ai_summary}</span>
                        </button>
                      </td>
                      <td className="px-2 py-3">
                        <span className="rounded-full bg-loss/20 px-2 py-1 font-mono text-[10px] text-loss">FIRED</span>
                      </td>
                      <td className="px-2 py-3 font-mono text-xs text-text-muted">
                        {new Date(item.fired_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
