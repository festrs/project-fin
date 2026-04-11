import { useState, useEffect } from "react";
import api from "../services/api";
import type { PortfolioSnapshot } from "../types";

type Period = "1D" | "1W" | "1M" | "1Y" | "ALL";

let _historyCache: Record<string, PortfolioSnapshot[]> = {};
let _latestCache: PortfolioSnapshot | null = null;

export function usePortfolioHistory(period: Period) {
  const [history, setHistory] = useState<PortfolioSnapshot[]>(_historyCache[period] || []);
  const [latestSnapshot, setLatestSnapshot] = useState<PortfolioSnapshot | null>(_latestCache);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      setError("");
      try {
        if (period === "1D") {
          const resp = await api.get<PortfolioSnapshot | null>("/portfolio/snapshot/latest");
          _latestCache = resp.data;
          setLatestSnapshot(resp.data);
        } else {
          const resp = await api.get<PortfolioSnapshot[]>("/portfolio/history", {
            params: { period },
          });
          _historyCache[period] = resp.data;
          setHistory(resp.data);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [period]);

  return { history, latestSnapshot, loading, error };
}
