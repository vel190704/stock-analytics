import { useCallback, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useStockStore } from '@/store/stockStore';
import type { StockEvent, WSStatus } from '@/types/stock';

function resolveWsUrl(): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  if (explicit && explicit.trim().length > 0) {
    const normalized = explicit.replace(/\/$/, '');
    return normalized.endsWith('/ws/stocks')
      ? normalized
      : `${normalized}/ws/stocks`;
  }

  const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
  if (apiUrl) {
    const url = new URL(apiUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws/stocks`;
  }

  return 'ws://localhost:8000/ws/stocks';
}

const WS_URL = resolveWsUrl();
const MAX_BACKOFF_MS = parseInt(
  import.meta.env.VITE_WS_RECONNECT_MAX_MS ?? '30000',
  10,
);

function isValidStockEvent(raw: Partial<StockEvent>): raw is StockEvent {
  return (
    typeof raw.ticker === 'string' &&
    typeof raw.event_time === 'string' &&
    raw.close != null &&
    raw.pct_change != null &&
    raw.price_change != null &&
    raw.volume != null
  );
}

export function useWebSocket(): {
  status: WSStatus;
  reconnect: () => void;
  disconnect: () => void;
} {
  const setWsStatus = useStockStore((s) => s.setWsStatus);
  const pushFeedEntry = useStockStore((s) => s.pushFeedEntry);
  const updatePrice = useStockStore((s) => s.updatePrice);
  const wsStatus = useStockStore((s) => s.wsStatus);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef<number>(1000);
  const intentionalCloseRef = useRef<boolean>(false);

  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  };

  const connect = useCallback(() => {
    // Avoid double-connecting
    if (
      socketRef.current !== null &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    intentionalCloseRef.current = false;
    setWsStatus('connecting');

    const ws = new WebSocket(WS_URL);
    socketRef.current = ws;

    ws.onopen = () => {
      console.info('[WS] connected to', WS_URL);
      setWsStatus('connected');
      backoffRef.current = 1000; // reset backoff on successful connect
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const raw = JSON.parse(event.data) as Partial<StockEvent> & {
          type?: string;
        };

        // Ignore server-sent pings
        if (raw.type === 'ping') return;

        if (!isValidStockEvent(raw)) {
          return;
        }

        const stockEvent = {
          ...raw,
          close: Number(raw.close),
          pct_change: Number(raw.pct_change),
          price_change: Number(raw.price_change),
          volume: Number(raw.volume),
        } as StockEvent;

        // Push to live feed ring buffer
        pushFeedEntry({
          id: uuidv4(),
          ticker: stockEvent.ticker,
          price: stockEvent.close,
          pct_change: stockEvent.pct_change,
          volume: stockEvent.volume,
          timestamp: stockEvent.event_time,
        });

        // Update latest price store
        updatePrice({
          ticker: stockEvent.ticker,
          latest_price: stockEvent.close,
          pct_change: stockEvent.pct_change,
          price_change: stockEvent.price_change,
          volume: stockEvent.volume,
          event_time: stockEvent.event_time,
        });
      } catch (err) {
        console.warn('[WS] failed to parse message:', err);
      }
    };

    ws.onerror = () => {
      console.error('[WS] error');
      setWsStatus('error');
    };

    ws.onclose = (event) => {
      socketRef.current = null;
      if (intentionalCloseRef.current) {
        setWsStatus('disconnected');
        return;
      }

      console.warn(`[WS] closed (code=${event.code}) — reconnecting in ${backoffRef.current}ms`);
      setWsStatus('disconnected');

      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, backoffRef.current);

      // Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (capped)
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
    };
  }, [pushFeedEntry, setWsStatus, updatePrice]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      socketRef.current?.close();
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    clearReconnectTimer();
    intentionalCloseRef.current = true;
    socketRef.current?.close();
    intentionalCloseRef.current = false;
    backoffRef.current = 1000;
    connect();
  }, [connect]);

  const disconnect = useCallback(() => {
    clearReconnectTimer();
    intentionalCloseRef.current = true;
    socketRef.current?.close();
    setWsStatus('disconnected');
  }, [setWsStatus]);

  return { status: wsStatus, reconnect, disconnect };
}
