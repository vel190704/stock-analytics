import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export interface SentimentTimelinePoint {
  time: string;
  score: number;
  price: number;
  headline: string;
}

export function SentimentTimeline({ data }: { data: SentimentTimelinePoint[] }) {
  if (!data.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-lg border border-border bg-bg-secondary">
        <span className="font-mono text-xs text-text-muted">No sentiment timeline data</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <h3 className="mb-3 font-sans text-lg font-semibold">Price + Sentiment Timeline</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <XAxis dataKey="time" tick={{ fill: '#7d8590', fontSize: 10 }} />
          <YAxis
            yAxisId="price"
            orientation="left"
            tick={{ fill: '#7d8590', fontSize: 10 }}
            tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
          />
          <YAxis
            yAxisId="sentiment"
            orientation="right"
            domain={[0, 1]}
            tick={{ fill: '#7d8590', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
            formatter={(value: number, name: string) => {
              if (name === 'price') return [`$${value.toFixed(2)}`, 'Price'];
              return [value.toFixed(3), 'Sentiment'];
            }}
            labelFormatter={(_, payload) => {
              const p = payload?.[0]?.payload;
              if (!p) return '';
              return `${p.time} | ${p.headline}`;
            }}
          />
          <Line yAxisId="price" type="monotone" dataKey="price" stroke="#58a6ff" dot={false} strokeWidth={2} />
          <Line yAxisId="sentiment" type="monotone" dataKey="score" stroke="#d29922" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
