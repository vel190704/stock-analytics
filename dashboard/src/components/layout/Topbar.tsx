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
        'relative z-20 flex h-14 items-center justify-between border-b border-border/70 bg-bg-secondary/80 px-4 backdrop-blur-xl lg:px-6',
        className,
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-accent/35 bg-accent/10">
          <BarChart2 className="h-4 w-4 text-accent" strokeWidth={2.2} />
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-sm font-semibold leading-none text-text-primary">
            Live Stock Analytics
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">
            Real-time cockpit
          </span>
        </div>
      </div>

      {/* Right cluster: clock + WS indicator */}
      <div className="flex items-center gap-3">
        <span className="rounded-full border border-border/70 bg-bg-card/60 px-2.5 py-1 font-mono text-[11px] text-text-muted">
          {format(now, 'HH:mm:ss')} UTC
        </span>
        <div className="flex items-center gap-2 rounded-full border border-border/70 bg-bg-card/60 px-2.5 py-1">
          <span className="font-sans text-[11px] text-text-muted">WS</span>
          <ConnectionDot
            status={status}
            onReconnect={reconnect}
          />
        </div>

        <div className="flex items-center gap-2 border-l border-border/60 pl-3">
          <Link
            to="/auth"
            className="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] text-text-primary transition-colors hover:bg-bg-card"
          >
            {hasToken ? 'Auth: Connected' : 'Auth: Required'}
          </Link>
          {hasToken && (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] text-text-muted transition-colors hover:bg-bg-card hover:text-text-primary"
            >
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
