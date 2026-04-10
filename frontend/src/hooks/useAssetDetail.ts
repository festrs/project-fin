import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type {
  Holding,
  Transaction,
  DividendHistoryItem,
  FundamentalsDetail,
} from "../types";

interface PricePoint {
  date: string;
  price: { amount: string; currency: string };
}

type Period = "1W" | "1M" | "3M" | "1Y" | "ALL";

const PERIOD_MAP: Record<Period, string> = {
  "1W": "5d",
  "1M": "1mo",
  "3M": "3mo",
  "1Y": "1y",
  ALL: "max",
};

export function useAssetDetail(
  symbol: string,
  country: string,
  assetClassId: string,
  type: string,
) {
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [holding, setHolding] = useState<Holding | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [dividends, setDividends] = useState<DividendHistoryItem[]>([]);
  const [fundamentals, setFundamentals] = useState<FundamentalsDetail | null>(
    null,
  );
  const [period, setPeriod] = useState<Period>("1M");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Fetch price history when period changes
  useEffect(() => {
    async function fetchHistory() {
      try {
        if (type === "crypto") {
          const days = { "1W": 7, "1M": 30, "3M": 90, "1Y": 365, ALL: 1825 }[
            period
          ];
          const resp = await api.get<PricePoint[]>(
            `/crypto/${symbol}/history`,
            { params: { days } },
          );
          setPriceHistory(resp.data);
        } else {
          const periodParam = PERIOD_MAP[period];
          const endpoint =
            country === "BR"
              ? `/stocks/br/${symbol}/history`
              : `/stocks/us/${symbol}/history`;
          const resp = await api.get<PricePoint[]>(endpoint, {
            params: { period: periodParam },
          });
          setPriceHistory(resp.data);
        }
      } catch {
        setPriceHistory([]);
      }
    }
    fetchHistory();
  }, [symbol, country, type, period]);

  // Fetch static data once
  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      setError("");
      try {
        const [holdingsResp, txResp] = await Promise.all([
          api.get<{ holdings: Holding[] }>("/portfolio/summary", {
            params: { live: true },
          }),
          api.get<Transaction[]>("/transactions", { params: { symbol } }),
        ]);

        const h =
          holdingsResp.data.holdings.find((item) => item.symbol === symbol) ||
          null;
        setHolding(h);
        setTransactions(txResp.data);

        // Dividends - may fail if no data
        try {
          const divResp = await api.get<{ items: DividendHistoryItem[] }>(
            "/dividends/history",
            {
              params: { asset_class_id: assetClassId },
            },
          );
          setDividends(
            (divResp.data.items || []).filter((d) => d.symbol === symbol),
          );
        } catch {
          setDividends([]);
        }

        // Fundamentals (only for stocks)
        if (type === "stock") {
          try {
            const fResp = await api.get<FundamentalsDetail>(
              `/fundamentals/${symbol}`,
            );
            setFundamentals(fResp.data);
          } catch {
            setFundamentals(null);
          }
        }
      } catch (e: unknown) {
        setError(
          e instanceof Error ? e.message : "Failed to load asset detail",
        );
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, [symbol, assetClassId, type]);

  const changePeriod = useCallback((p: Period) => setPeriod(p), []);

  return {
    priceHistory,
    holding,
    transactions,
    dividends,
    fundamentals,
    period,
    changePeriod,
    loading,
    error,
  };
}
