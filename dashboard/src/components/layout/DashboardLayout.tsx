import { Outlet } from 'react-router-dom';
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
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg-primary font-sans text-text-primary">
      <Topbar />
      <TickerTape />

      {/* Sidebar + page content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar className="hidden lg:flex" />
        <main className="flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
