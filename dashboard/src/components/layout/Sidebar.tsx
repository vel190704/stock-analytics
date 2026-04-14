import { NavLink } from 'react-router-dom';
import {
  Activity,
  KeyRound,
  BarChart2,
  Bell,
  FlaskConical,
  Gauge,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { useStockStore } from '@/store/stockStore';
import { cn } from '@/lib/utils';

interface SidebarProps {
  className?: string;
}

const navItems = [
  {
    label: 'Dashboard',
    to: '/',
    icon: BarChart2,
  },
  {
    label: 'Top Gainers',
    to: '/gainers',
    icon: TrendingUp,
  },
  {
    label: 'Top Losers',
    to: '/losers',
    icon: TrendingDown,
  },
  {
    label: 'Live Feed',
    to: '/feed',
    icon: Activity,
  },
  {
    label: 'Alerts',
    to: '/alerts',
    icon: Bell,
  },
  {
    label: 'Auth',
    to: '/auth',
    icon: KeyRound,
  },
  {
    label: 'Portfolio',
    to: '/portfolio',
    icon: Wallet,
  },
  {
    label: 'Sentiment',
    to: '/sentiment',
    icon: Gauge,
  },
  {
    label: 'Backtest',
    to: '/backtest',
    icon: FlaskConical,
  },
];

export function Sidebar({ className }: SidebarProps) {
  const wsStatus = useStockStore((s) => s.wsStatus);

  const statusLabel =
    wsStatus === 'connected'
      ? 'Live'
      : wsStatus === 'connecting'
        ? 'Connecting'
        : 'Offline';

  const statusColour =
    wsStatus === 'connected'
      ? 'bg-gain'
      : wsStatus === 'connecting'
        ? 'bg-amber'
        : 'bg-loss';

  return (
    <aside
      className={cn(
        'flex w-52 flex-col border-r border-border bg-bg-secondary',
        className,
      )}
    >
      {/* Navigation links */}
      <nav className="flex-1 px-2 py-4">
        <ul className="space-y-1">
          {navItems.map(({ label, to, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 font-sans text-sm transition-colors',
                    isActive
                      ? 'bg-accent/10 text-accent'
                      : 'text-text-muted hover:bg-bg-card hover:text-text-primary',
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Connection status badge at the bottom */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={cn('h-2 w-2 rounded-full', statusColour)} />
          <span className="font-sans text-xs text-text-muted">{statusLabel}</span>
        </div>
      </div>
    </aside>
  );
}
