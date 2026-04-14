import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { BarChart2 } from 'lucide-react';
import { clearAuthToken, getAuthToken } from '@/api/client';
import { ConnectionDot } from '@/components/ui/ConnectionDot';
import { useWebSocket } from '@/hooks/useWebSocket';
import { cn } from '@/lib/utils';

interface TopbarProps {
  className?: string;
}

export function Topbar({ className }: TopbarProps) {
  const { status, reconnect } = useWebSocket();
  const [now, setNow] = useState<Date>(new Date());
  const [hasToken, setHasToken] = useState<boolean>(Boolean(getAuthToken()));

  // Update the clock every second
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setHasToken(Boolean(getAuthToken())), 1000);
    return () => clearInterval(id);
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    setHasToken(false);
  };

  return (
    <header
      className={cn(
        'flex h-12 items-center justify-between border-b border-border bg-bg-secondary px-4',
        className,
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-2">
        <BarChart2 className="h-5 w-5 text-accent" strokeWidth={2} />
        <span className="font-sans text-sm font-semibold text-text-primary">
          Live Stock Analytics
        </span>
      </div>

      {/* Right cluster: clock + WS indicator */}
      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-text-muted">
          {format(now, 'HH:mm:ss')} UTC
        </span>
        <div className="flex items-center gap-2">
          <span className="font-sans text-xs text-text-muted">WS</span>
          <ConnectionDot
            status={status}
            onReconnect={reconnect}
          />
        </div>

        <div className="flex items-center gap-2 border-l border-border/60 pl-3">
          <Link
            to="/auth"
            className="rounded border border-border px-2 py-1 font-mono text-[11px] text-text-primary hover:bg-bg-card"
          >
            {hasToken ? 'Auth: Connected' : 'Auth: Required'}
          </Link>
          {hasToken && (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded border border-border px-2 py-1 font-mono text-[11px] text-text-muted hover:text-text-primary"
            >
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
