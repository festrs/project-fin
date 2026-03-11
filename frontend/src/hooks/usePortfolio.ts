import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { Holding } from "../types";

interface AllocationEntry {
  asset_class_id: string;
  class_name: string;
  actual_weight: number;
  target_weight: number;
}

export function usePortfolio() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [allocation, setAllocation] = useState<AllocationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, allocationRes] = await Promise.all([
        api.get<{ holdings: Holding[] }>("/portfolio/summary"),
        api.get<{ allocation: AllocationEntry[] }>("/portfolio/allocation"),
      ]);
      setHoldings(summaryRes.data.holdings);
      setAllocation(allocationRes.data.allocation);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { holdings, allocation, loading, error, refresh };
}
