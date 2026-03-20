import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { AssetClass } from "../types";

let _cache: AssetClass[] | null = null;

export function useAssetClasses() {
  const [assetClasses, setAssetClasses] = useState<AssetClass[]>(_cache ?? []);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  const fetchClasses = useCallback(async () => {
    try {
      if (!_cache) setLoading(true);
      const res = await api.get<AssetClass[]>("/asset-classes");
      _cache = res.data;
      setAssetClasses(res.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch asset classes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClasses();
  }, [fetchClasses]);

  const createClass = useCallback(async (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income" = "stock") => {
    const res = await api.post<AssetClass>("/asset-classes", {
      name,
      target_weight: targetWeight,
      type,
    });
    setAssetClasses((prev) => { _cache = [...prev, res.data]; return _cache; });
    return res.data;
  }, []);

  const updateClass = useCallback(async (id: string, data: Partial<AssetClass>) => {
    const res = await api.put<AssetClass>(`/asset-classes/${id}`, data);
    setAssetClasses((prev) => { _cache = prev.map((c) => (c.id === id ? res.data : c)); return _cache; });
    return res.data;
  }, []);

  const deleteClass = useCallback(async (id: string) => {
    await api.delete(`/asset-classes/${id}`);
    setAssetClasses((prev) => { _cache = prev.filter((c) => c.id !== id); return _cache; });
  }, []);

  return { assetClasses, loading, error, createClass, updateClass, deleteClass, refresh: fetchClasses };
}
