import type { SentimentScore } from '@/types/stock';

function badgeColor(label: SentimentScore['label']): string {
  if (label === 'bullish') return 'bg-gain/20 text-gain';
  if (label === 'bearish') return 'bg-loss/20 text-loss';
  return 'bg-bg-card text-text-muted';
}

export function SentimentFeed({ data }: { data: SentimentScore[] }) {
  return (
    <div className="panel-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-sans text-lg font-semibold">Recent Sentiment Feed</h3>
        <span className="rounded-full border border-border/70 bg-bg-card/70 px-2 py-1 font-mono text-[10px] text-text-muted">
          Powered by Claude AI
        </span>
      </div>

      <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
        {data.map((item) => (
          <a
            key={item.id}
            href={item.source_url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-xl border border-border/60 bg-bg-card/70 p-3 transition-colors hover:border-accent/60"
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className={`rounded-full px-2 py-1 font-mono text-[10px] uppercase ${badgeColor(item.label)}`}>
                {item.label} {Math.round(item.score * 100)}
              </span>
              <span className="font-mono text-[10px] text-text-muted">
                {new Date(item.scored_at).toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-text-primary">{item.headline}</p>
            <p className="mt-1 text-xs text-text-muted">{item.reason}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
