import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { TickerTape } from '@/components/ticker/TickerTape';

/**
 * Shell layout: fixed Topbar → scrolling TickerTape → Sidebar + content.
 *
 * CSS Grid structure:
 *   [topbar  — full width, fixed height 48px       ]
 *   [tape    — full width, fixed height 36px        ]
 *   [sidebar | main content — fills remaining height]
 */
export function DashboardLayout() {
  const location = useLocation();

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-bg-primary font-sans text-text-primary">
      <div className="pointer-events-none absolute inset-0 opacity-60">
        <div className="absolute -top-28 left-8 h-72 w-72 rounded-full bg-accent/20 blur-3xl" />
        <div className="absolute right-8 top-10 h-64 w-64 rounded-full bg-gain/10 blur-3xl" />
      </div>
      <Topbar />
      <TickerTape />

      {/* Sidebar + page content */}
      <div className="relative z-10 flex flex-1 overflow-hidden">
        <Sidebar className="hidden lg:flex" />
        <main className="flex-1 overflow-y-auto px-4 pb-5 pt-4 lg:px-6 lg:pb-6">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
