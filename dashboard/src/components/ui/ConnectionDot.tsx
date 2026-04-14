import { cn } from '@/lib/utils';
import type { WSStatus } from '@/types/stock';

interface ConnectionDotProps {
  status: WSStatus;
  onReconnect?: () => void;
  className?: string;
}

const statusConfig: Record<
  WSStatus,
  { dotClass: string; label: string; showReconnect: boolean }
> = {
  connected: {
    dotClass: 'bg-gain animate-pulse-fast',
    label: 'Connected',
    showReconnect: false,
  },
  connecting: {
    dotClass: 'bg-amber animate-pulse-slow',
    label: 'Connecting…',
    showReconnect: false,
  },
  disconnected: {
    dotClass: 'bg-loss',
    label: 'Disconnected',
    showReconnect: true,
  },
  error: {
    dotClass: 'bg-loss',
    label: 'Connection error',
    showReconnect: true,
  },
};

/**
 * 8px circle indicator in the Topbar showing WebSocket connection status.
 *
 * - Green + fast pulse  = connected
 * - Amber + slow pulse  = connecting / reconnecting
 * - Red (no animation) = disconnected / error
 *
 * Clicking it when disconnected triggers `onReconnect`.
 */
export function ConnectionDot({
  status,
  onReconnect,
  className,
}: ConnectionDotProps) {
  const config = statusConfig[status];

  return (
    <div className={cn('group relative flex items-center gap-2', className)}>
      {/* The dot itself */}
      <span
        className={cn('block h-2 w-2 rounded-full', config.dotClass)}
        aria-label={`WebSocket: ${config.label}`}
      />

      {/* Hover tooltip */}
      <span className="pointer-events-none absolute right-0 top-5 z-50 hidden w-max max-w-[180px] rounded bg-bg-card px-2 py-1 text-xs text-text-primary shadow-lg group-hover:block">
        {config.label}
        {config.showReconnect && onReconnect && (
          <>
            {' '}
            —{' '}
            <button
              onClick={onReconnect}
              className="pointer-events-auto text-accent underline"
            >
              Reconnect
            </button>
          </>
        )}
      </span>
    </div>
  );
}
