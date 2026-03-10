import { useState, useCallback } from "react";
import api from "../services/api";

interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  currency: string;
  market_cap: number;
}

interface CryptoQuote {
  coin_id: string;
  name: string;
  price: number;
  currency: string;
  market_cap: number;
}

interface HistoryEntry {
  date: string;
  price: number;
}

export type Quote = StockQuote | CryptoQuote;

export function useMarketData() {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchStock = useCallback(async (symbol: string) => {
    try {
      setLoading(true);
      setError(null);
      const [quoteRes, historyRes] = await Promise.all([
        api.get<StockQuote>(`/stocks/${symbol}`),
        api.get<HistoryEntry[]>(`/stocks/${symbol}/history`, {
          params: { period: "1mo" },
        }),
      ]);
      setQuote(quoteRes.data);
      setHistory(historyRes.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stock data");
      setQuote(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const searchCrypto = useCallback(async (coinId: string) => {
    try {
      setLoading(true);
      setError(null);
      const [quoteRes, historyRes] = await Promise.all([
        api.get<CryptoQuote>(`/crypto/${coinId}`),
        api.get<HistoryEntry[]>(`/crypto/${coinId}/history`, {
          params: { days: 30 },
        }),
      ]);
      setQuote(quoteRes.data);
      setHistory(historyRes.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch crypto data");
      setQuote(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { quote, history, loading, error, searchStock, searchCrypto };
}
