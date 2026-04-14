import { useMemo } from 'react';

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function SentimentGauge({
  score,
  label,
  updatedAt,
}: {
  score: number;
  label: string;
  updatedAt: string;
}) {
  const clamped = Math.min(1, Math.max(0, score));
  const pct = clamped * 100;
  const needleAngle = 180 * clamped;

  const needle = useMemo(() => {
    const c = polarToCartesian(120, 120, 85, needleAngle);
    return `${120},120 ${c.x},${c.y}`;
  }, [needleAngle]);

  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <h3 className="mb-2 font-sans text-lg font-semibold">Sentiment Gauge</h3>
      <svg width="100%" viewBox="0 0 240 150" className="mx-auto max-w-[320px]">
        <defs>
          <linearGradient id="sentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f85149" />
            <stop offset="50%" stopColor="#d29922" />
            <stop offset="100%" stopColor="#3fb950" />
          </linearGradient>
        </defs>
        <path d="M20 120 A100 100 0 0 1 220 120" stroke="url(#sentGrad)" strokeWidth="14" fill="none" strokeLinecap="round" />
        <line x1="120" y1="120" x2={needle.split(' ')[1].split(',')[0]} y2={needle.split(' ')[1].split(',')[1]} stroke="#e6edf3" strokeWidth="3" />
        <circle cx="120" cy="120" r="6" fill="#e6edf3" />
      </svg>
      <div className="mt-2 text-center">
        <p className="font-mono text-3xl font-bold text-text-primary">{pct.toFixed(1)}</p>
        <p className="font-mono text-xs uppercase tracking-wide text-text-muted">{label}</p>
        <p className="mt-1 font-mono text-xs text-text-muted">
          Updated {new Date(updatedAt).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
