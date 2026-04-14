import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Interval, LiveFeedEntry, TickerSummary, WSStatus } from '@/types/stock';

const FEED_MAX = parseInt(
  import.meta.env.VITE_FEED_MAX_ENTRIES ?? '200',
  10,
);

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface StockStore {
  // WebSocket connection state
  wsStatus: WSStatus;
  setWsStatus: (status: WSStatus) => void;

  // Live feed (ring buffer — max FEED_MAX entries)
  liveFeed: LiveFeedEntry[];
  pushFeedEntry: (entry: LiveFeedEntry) => void;
  clearFeed: () => void;

  // Latest price per ticker (updated on every WS event)
  latestPrices: Record<string, TickerSummary>;
  updatePrice: (summary: TickerSummary) => void;

  // Selected ticker for detail / chart view
  selectedTicker: string;
  setSelectedTicker: (ticker: string) => void;

  // Selected chart interval
  selectedInterval: Interval;
  setSelectedInterval: (interval: Interval) => void;
}

// ---------------------------------------------------------------------------
// Store implementation
// ---------------------------------------------------------------------------

export const useStockStore = create<StockStore>()(
  immer((set) => ({
    wsStatus: 'disconnected',
    setWsStatus: (status) =>
      set((state) => {
        state.wsStatus = status;
      }),

    liveFeed: [],
    pushFeedEntry: (entry) =>
      set((state) => {
        if (state.liveFeed.length >= FEED_MAX) {
          state.liveFeed.shift(); // drop oldest
        }
        state.liveFeed.push(entry);
      }),
    clearFeed: () =>
      set((state) => {
        state.liveFeed = [];
      }),

    latestPrices: {},
    updatePrice: (summary) =>
      set((state) => {
        state.latestPrices[summary.ticker] = summary;
      }),

    selectedTicker: 'AAPL',
    setSelectedTicker: (ticker) =>
      set((state) => {
        state.selectedTicker = ticker;
      }),

    selectedInterval: '1m',
    setSelectedInterval: (interval) =>
      set((state) => {
        state.selectedInterval = interval;
      }),
  })),
);
