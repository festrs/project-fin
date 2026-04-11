import { useState, useEffect } from "react";
import api from "../services/api";
import type { TaxMonthlyEntry } from "../types";

export function useTaxReport(year: number) {
  const [report, setReport] = useState<TaxMonthlyEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      setError("");
      try {
        const resp = await api.get<TaxMonthlyEntry[]>("/tax/report", { params: { year } });
        setReport(resp.data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load tax report");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [year]);

  return { report, loading, error };
}
