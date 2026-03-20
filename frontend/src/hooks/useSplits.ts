import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { StockSplit } from "../types";

let _splitsCache: StockSplit[] | null = null;

export function useSplits() {
  const [pendingSplits, setPendingSplits] = useState<StockSplit[]>(_splitsCache ?? []);
  const [loading, setLoading] = useState(!_splitsCache);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const refresh = useCallback(async () => {
    try {
      if (!_splitsCache) setLoading(true);
      const res = await api.get<StockSplit[]>("/splits/pending");
      _splitsCache = res.data;
      setPendingSplits(_splitsCache);
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
    setActionLoading((prev) => ({ ...prev, [splitId]: true }));
    try {
      await api.post(`/splits/${splitId}/apply`);
      await refresh();
    } finally {
      setActionLoading((prev) => ({ ...prev, [splitId]: false }));
    }
  }, [refresh]);

  const dismissSplit = useCallback(async (splitId: string) => {
    setActionLoading((prev) => ({ ...prev, [splitId]: true }));
    try {
      await api.post(`/splits/${splitId}/dismiss`);
      await refresh();
    } finally {
      setActionLoading((prev) => ({ ...prev, [splitId]: false }));
    }
  }, [refresh]);

  return { pendingSplits, loading, actionLoading, applySplit, dismissSplit, refresh };
}
