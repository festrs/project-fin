import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { Recommendation } from "../types";

let _recsCache: Recommendation[] | null = null;

export function useRecommendations(count: number = 2) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>(_recsCache ?? []);
  const [loading, setLoading] = useState(!_recsCache);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      if (!_recsCache) setLoading(true);
      const res = await api.get<{ recommendations: Recommendation[] }>("/recommendations", {
        params: { count },
      });
      _recsCache = res.data.recommendations;
      setRecommendations(_recsCache);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch recommendations");
    } finally {
      setLoading(false);
    }
  }, [count]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { recommendations, loading, error, refresh };
}
