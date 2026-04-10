import { useState, useEffect } from "react";
import api from "../services/api";
import type { MarketMoversResponse } from "../types";

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

let _cache: MarketMoversResponse | null = null;
let _cacheTime = 0;

function isCacheFresh(): boolean {
  return _cache !== null && Date.now() - _cacheTime < CACHE_TTL_MS;
}

export function useMarketMovers() {
  const [movers, setMovers] = useState<MarketMoversResponse>(
    _cache ?? { gainers: [], losers: [] }
  );
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isCacheFresh()) return;

    api
      .get<MarketMoversResponse>("/market/movers")
      .then((res) => {
        _cache = res.data;
        _cacheTime = Date.now();
        setMovers(_cache);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to fetch market movers"
        );
      })
      .finally(() => setLoading(false));
  }, []);

  return { movers, loading, error };
}
