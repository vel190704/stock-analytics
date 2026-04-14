import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export interface PortfolioValuePoint {
  time: string;
  value: number;
}

export function PortfolioChart({ data }: { data: PortfolioValuePoint[] }) {
  if (!data.length) {
    return (
      <div className="panel-surface flex h-[280px] items-center justify-center">
        <span className="font-mono text-xs text-text-muted">No portfolio value history yet</span>
      </div>
    );
  }

  const start = data[0].value || 1;
  const enriched = data.map((row) => ({
    ...row,
    above: row.value >= start ? row.value : start,
    below: row.value < start ? row.value : start,
    baseline: start,
    pct: ((row.value - start) / start) * 100,
  }));

  return (
    <div className="panel-surface p-4">
      <h3 className="mb-3 font-sans text-lg font-semibold text-text-primary">Portfolio Value Over Time</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={enriched}>
          <defs>
            <linearGradient id="gainFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3fb950" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#3fb950" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="lossFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f85149" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#f85149" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(146,168,198,0.2)" strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fill: '#7d8590', fontSize: 10 }} />
          <YAxis tick={{ fill: '#7d8590', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
            formatter={(value: number, name) => {
              if (name === 'value') {
                return [`$${value.toFixed(2)}`, 'Value'];
              }
              return [value, name];
            }}
            labelFormatter={(_, payload) => {
              const p = payload?.[0]?.payload;
              if (!p) return '';
              const sign = p.pct >= 0 ? '+' : '';
              return `${p.time} (${sign}${p.pct.toFixed(2)}%)`;
            }}
          />
          <Area type="monotone" dataKey="above" stroke="#3fb950" fill="url(#gainFill)" dot={false} />
          <Area type="monotone" dataKey="below" stroke="#f85149" fill="url(#lossFill)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
