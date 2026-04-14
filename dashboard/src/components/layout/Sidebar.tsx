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
        'flex w-60 flex-col border-r border-border/70 bg-bg-secondary/70 backdrop-blur-xl',
        className,
      )}
    >
      {/* Navigation links */}
      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {navItems.map(({ label, to, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 rounded-xl px-3 py-2.5 font-sans text-sm transition-all',
                    isActive
                      ? 'bg-gradient-to-r from-accent/20 to-accent/5 text-accent shadow-[inset_0_0_0_1px_rgba(120,178,255,0.3)]'
                      : 'text-text-muted hover:bg-bg-card/80 hover:text-text-primary',
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" strokeWidth={1.8} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Connection status badge at the bottom */}
      <div className="border-t border-border/70 px-4 py-3">
        <div className="flex items-center gap-2 rounded-xl border border-border/70 bg-bg-card/40 px-3 py-2">
          <span className={cn('h-2 w-2 rounded-full', statusColour)} />
          <span className="font-sans text-xs text-text-muted">{statusLabel}</span>
        </div>
      </div>
    </aside>
  );
}
