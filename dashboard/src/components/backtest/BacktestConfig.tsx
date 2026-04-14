import { FormEvent, useMemo, useState } from 'react';
import { useTickerList } from '@/hooks/useStockData';

type Strategy = 'ma_crossover' | 'rsi_oversold' | 'breakout';

interface BacktestConfigProps {
  isRunning: boolean;
  onRun: (payload: {
    ticker: string;
    strategy: Strategy;
    params: Record<string, number>;
    start_date: string;
    end_date: string;
    initial_capital: number;
  }) => void;
}

export function BacktestConfig({ isRunning, onRun }: BacktestConfigProps) {
  const { data: tickerResp } = useTickerList();
  const tickers = useMemo(() => (tickerResp?.data ?? []).map((item) => item.ticker), [tickerResp]);

  const [ticker, setTicker] = useState('AAPL');
  const [strategy, setStrategy] = useState<Strategy>('ma_crossover');
  const [startDate, setStartDate] = useState(() => new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [initialCapital, setInitialCapital] = useState('10000');
  const [params, setParams] = useState<Record<string, string>>({
    fast_window: '10',
    slow_window: '20',
    rsi_period: '14',
    oversold: '30',
    overbought: '70',
    lookback: '20',
  });

  const strategyParams = useMemo(() => {
    if (strategy === 'ma_crossover') {
      return [
        { key: 'fast_window', label: 'Fast MA Window' },
        { key: 'slow_window', label: 'Slow MA Window' },
      ];
    }
    if (strategy === 'rsi_oversold') {
      return [
        { key: 'rsi_period', label: 'RSI Period' },
        { key: 'oversold', label: 'Oversold' },
        { key: 'overbought', label: 'Overbought' },
      ];
    }
    return [{ key: 'lookback', label: 'Breakout Lookback' }];
  }, [strategy]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const cleanParams = Object.fromEntries(strategyParams.map((param) => [param.key, Number(params[param.key]) || 0]));

    onRun({
      ticker,
      strategy,
      params: cleanParams,
      start_date: new Date(`${startDate}T00:00:00Z`).toISOString(),
      end_date: new Date(`${endDate}T23:59:59Z`).toISOString(),
      initial_capital: Number(initialCapital),
    });
  };

  return (
    <form onSubmit={submit} className="panel-surface bg-gradient-to-r from-accent/10 to-transparent p-4">
      <h3 className="mb-3 font-sans text-lg font-semibold">Backtest Configuration</h3>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <label className="mb-1 block font-mono text-xs text-text-muted">Ticker</label>
          <select
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
          <label className="mb-1 block font-mono text-xs text-text-muted">Strategy</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as Strategy)}
            className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
          >
            <option value="ma_crossover">MA Crossover</option>
            <option value="rsi_oversold">RSI Oversold</option>
            <option value="breakout">Breakout</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block font-mono text-xs text-text-muted">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="mb-1 block font-mono text-xs text-text-muted">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        {strategyParams.map((param) => (
          <div key={param.key}>
            <label className="mb-1 block font-mono text-xs text-text-muted">{param.label}</label>
            <input
              type="number"
              value={params[param.key]}
              onChange={(e) =>
                setParams((prev) => ({
                  ...prev,
                  [param.key]: e.target.value,
                }))
              }
              className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
            />
          </div>
        ))}

        <div>
          <label className="mb-1 block font-mono text-xs text-text-muted">Initial Capital</label>
          <input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(e.target.value)}
            className="w-full rounded border border-border bg-bg-card px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={isRunning}
          className="rounded-md bg-accent px-4 py-2 font-mono text-xs font-semibold text-black disabled:opacity-70"
        >
          {isRunning ? 'Running…' : 'Run Backtest'}
        </button>
      </div>
    </form>
  );
}
