import { useState } from "react";
import api from "../services/api";
import type { InvestmentPlan } from "../types";

export function useInvest() {
  const [plan, setPlan] = useState<InvestmentPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = async (amount: string, currency: string, count: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post<InvestmentPlan>("/recommendations/invest", {
        amount,
        currency,
        count,
      });
      setPlan(res.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to calculate investment plan";
      setError(message);
      setPlan(null);
    } finally {
      setLoading(false);
    }
  };

  return { plan, loading, error, calculate };
}
