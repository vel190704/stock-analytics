import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  subValue?: string;
  valueClassName?: string;
  className?: string;
}

/**
 * Reusable metric card used in the TickerDetailPage stats row
 * and wherever a single KPI needs to be surfaced.
 */
export function StatCard({
  title,
  value,
  subValue,
  valueClassName,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-1 rounded-lg border border-border bg-bg-card px-4 py-3',
        className,
      )}
    >
      <span className="font-sans text-xs font-medium uppercase tracking-wider text-text-muted">
        {title}
      </span>
      <span
        className={cn(
          'font-mono text-xl font-semibold text-text-primary',
          valueClassName,
        )}
      >
        {value}
      </span>
      {subValue && (
        <span className="font-mono text-xs text-text-muted">{subValue}</span>
      )}
    </div>
  );
}
