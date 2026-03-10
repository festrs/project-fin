import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import { Recommendation } from "../types";

export function useRecommendations(count: number = 2) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<Recommendation[]>("/recommendations", {
        params: { count },
      });
      setRecommendations(res.data);
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
