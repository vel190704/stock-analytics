import { cn, formatPct } from '@/lib/utils';

interface PriceChangeProps {
  value: number | null | undefined;
  showArrow?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-0.5',
  lg: 'text-base px-2.5 py-1',
};

/**
 * Coloured percentage-change badge with optional ▲▼ directional arrow.
 *
 * Green background for gains, red for losses, muted for zero.
 */
export function PriceChange({
  value,
  showArrow = true,
  size = 'md',
  className,
}: PriceChangeProps) {
  const isPositive = (value ?? 0) > 0;
  const isNegative = (value ?? 0) < 0;

  const colourClasses = isPositive
    ? 'text-gain bg-gain/10 border border-gain/20'
    : isNegative
      ? 'text-loss bg-loss/10 border border-loss/20'
      : 'text-text-muted bg-text-muted/10 border border-text-muted/20';

  const arrow = showArrow ? (isPositive ? '▲' : isNegative ? '▼' : '—') : '';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded font-mono font-medium',
        sizeClasses[size],
        colourClasses,
        className,
      )}
    >
      {arrow && <span>{arrow}</span>}
      <span>{formatPct(value)}</span>
    </span>
  );
}
