import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { StockSplit } from "../types";

export function useSplits() {
  const [pendingSplits, setPendingSplits] = useState<StockSplit[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<StockSplit[]>("/splits/pending");
      setPendingSplits(res.data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const applySplit = useCallback(async (splitId: string) => {
    await api.post(`/splits/${splitId}/apply`);
    await refresh();
  }, [refresh]);

  const dismissSplit = useCallback(async (splitId: string) => {
    await api.post(`/splits/${splitId}/dismiss`);
    await refresh();
  }, [refresh]);

  return { pendingSplits, loading, applySplit, dismissSplit, refresh };
}
