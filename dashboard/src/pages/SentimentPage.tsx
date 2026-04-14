import { useMemo, useState } from 'react';
import { SentimentFeed } from '@/components/sentiment/SentimentFeed';
import { SentimentGauge } from '@/components/sentiment/SentimentGauge';
import { SentimentTimeline } from '@/components/sentiment/SentimentTimeline';
import { useSentiment, useSentimentAggregate, useTickerHistory, useTickerList } from '@/hooks/useStockData';

export function SentimentPage() {
  const { data: tickersResp } = useTickerList();
  const [ticker, setTicker] = useState('AAPL');

  const { data: sentiment = [] } = useSentiment(ticker);
  const { data: aggregate } = useSentimentAggregate(ticker);
  const { data: history } = useTickerHistory(ticker, '1m', 200);

  const tickers = useMemo(() => (tickersResp?.data ?? []).map((item) => item.ticker), [tickersResp]);

  const gaugeScore = aggregate?.avg_24h ?? 0.5;
  const gaugeLabel = gaugeScore > 0.55 ? 'Bullish' : gaugeScore < 0.45 ? 'Bearish' : 'Neutral';
  const updatedAt = sentiment[0]?.scored_at ?? new Date().toISOString();

  const timelineData = useMemo(() => {
    const prices = history?.data ?? [];
    if (!sentiment.length || !prices.length) return [];

    return sentiment.slice(0, 40).map((item, index) => {
      const pricePoint = prices[Math.max(0, prices.length - 1 - index)] ?? prices[prices.length - 1];
      return {
        time: new Date(item.scored_at).toLocaleTimeString(),
        score: item.score,
        price: pricePoint.close,
        headline: item.headline,
      };
    }).reverse();
  }, [history, sentiment]);

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-border bg-bg-secondary p-4">
        <label className="mb-1 block font-mono text-xs text-text-muted">Ticker</label>
        <select
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          className="w-full max-w-xs rounded border border-border bg-bg-card px-3 py-2 text-sm"
        >
          {tickers.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_1fr]">
        <SentimentGauge score={gaugeScore} label={gaugeLabel} updatedAt={updatedAt} />
        <SentimentTimeline data={timelineData} />
      </div>

      <SentimentFeed data={sentiment} />
    </div>
  );
}
