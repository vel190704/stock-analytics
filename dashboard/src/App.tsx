import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { AuthPage } from '@/pages/AuthPage';
import { BacktestPage } from '@/pages/BacktestPage';
import { PortfolioPage } from '@/pages/PortfolioPage';
import { SentimentPage } from '@/pages/SentimentPage';
import { TickerDetailPage } from '@/pages/TickerDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="/ticker/:symbol" element={<TickerDetailPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/sentiment" element={<SentimentPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
            {/* Redirect legacy /gainers and /losers to dashboard */}
            <Route path="/gainers" element={<Navigate to="/" replace />} />
            <Route path="/losers" element={<Navigate to="/" replace />} />
            <Route path="/feed" element={<DashboardPage />} />
            {/* Catch-all → dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
