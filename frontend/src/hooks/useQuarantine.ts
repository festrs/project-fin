import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { QuarantineConfig, QuarantineStatus } from "../types";

export function useQuarantine() {
  const [config, setConfig] = useState<QuarantineConfig | null>(null);
  const [statuses, setStatuses] = useState<QuarantineStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const [configRes, statusRes] = await Promise.all([
        api.get<QuarantineConfig>("/quarantine/config"),
        api.get<QuarantineStatus[]>("/quarantine/status"),
      ]);
      setConfig(configRes.data);
      setStatuses(statusRes.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch quarantine data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const updateConfig = useCallback(
    async (threshold: number, periodDays: number) => {
      const res = await api.put<QuarantineConfig>("/quarantine/config", {
        threshold,
        period_days: periodDays,
      });
      setConfig(res.data);
      return res.data;
    },
    []
  );

  return { config, statuses, loading, error, updateConfig, refresh };
}
