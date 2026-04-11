import { useState, useEffect } from "react";
import api from "../services/api";
import type { MarketIndex } from "../types";

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

let _cache: MarketIndex[] | null = null;
let _cacheTime = 0;

function isCacheFresh(): boolean {
  return _cache !== null && Date.now() - _cacheTime < CACHE_TTL_MS;
}

export function useMarketIndices() {
  const [indices, setIndices] = useState<MarketIndex[]>(_cache ?? []);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isCacheFresh()) return;

    api
      .get<MarketIndex[]>("/market/indices")
      .then((res) => {
        _cache = res.data;
        _cacheTime = Date.now();
        setIndices(_cache);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to fetch market indices"
        );
      })
      .finally(() => setLoading(false));
  }, []);

  return { indices, loading, error };
}
