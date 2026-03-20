import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type { FundamentalsDetail, FundamentalsScore } from "../types";

let _scoresCache: FundamentalsScore[] | null = null;

export function useFundamentals() {
  const [scores, setScores] = useState<FundamentalsScore[]>(_scoresCache ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScores = useCallback(async () => {
    try {
      if (!_scoresCache) setLoading(true);
      const resp = await api.get<FundamentalsScore[]>("/fundamentals/scores");
      _scoresCache = resp.data;
      setScores(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch scores");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  const refreshAll = useCallback(async () => {
    try {
      setLoading(true);
      await api.post("/fundamentals/refresh-all");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start refresh");
    } finally {
      setLoading(false);
    }
  }, []);

  return { scores, loading, error, refresh: fetchScores, refreshAll };
}

export function useFundamentalsDetail(symbol: string) {
  const [detail, setDetail] = useState<FundamentalsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await api.get<FundamentalsDetail>(`/fundamentals/${symbol}`);
      setDetail(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch detail");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  const refreshScore = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await api.post<FundamentalsDetail>(
        `/fundamentals/${symbol}/refresh`
      );
      setDetail(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh score");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  return { detail, loading, error, refresh: refreshScore };
}
