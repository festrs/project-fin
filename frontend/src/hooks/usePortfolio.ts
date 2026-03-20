import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { Holding, Money } from "../types";
import { moneyToNumber } from "../utils/money";

interface AllocationAsset {
  symbol: string;
  quantity: number;
  total_cost: Money;
  target_weight: number;
}

interface AllocationApiEntry {
  class_id: string;
  class_name: string;
  target_weight: number;
  assets: AllocationAsset[];
}

export interface AllocationEntry {
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

  const fetchSummary = useCallback(async (live: boolean) => {
    const [summaryRes, allocationRes] = await Promise.all([
      api.get<{ holdings: Holding[] }>("/portfolio/summary", { params: { live } }),
      api.get<{ allocation: AllocationApiEntry[] }>("/portfolio/allocation"),
    ]);
    setHoldings(summaryRes.data.holdings);

    const rawAlloc = allocationRes.data.allocation;
    const grandTotal = rawAlloc.reduce(
      (sum, entry) => sum + entry.assets.reduce((s, a) => s + moneyToNumber(a.total_cost), 0),
      0
    );

    const computed: AllocationEntry[] = rawAlloc.map((entry) => {
      const classTotal = entry.assets.reduce((s, a) => s + moneyToNumber(a.total_cost), 0);
      return {
        asset_class_id: entry.class_id,
        class_name: entry.class_name,
        target_weight: entry.target_weight,
        actual_weight: grandTotal > 0 ? (classTotal / grandTotal) * 100 : 0,
      };
    });

    setAllocation(computed);
  }, []);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      // Phase 1: Load cached data instantly
      await fetchSummary(false);
      setLoading(false);
      // Phase 2: Refresh with live prices in background
      await fetchSummary(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch portfolio");
    } finally {
      setLoading(false);
    }
  }, [fetchSummary]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { holdings, allocation, loading, error, refresh };
}
