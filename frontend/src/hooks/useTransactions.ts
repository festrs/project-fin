import { useState, useCallback } from "react";
import api from "../services/api";
import { Transaction } from "../types";

export function useTransactions(symbol?: string) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async (sym?: string) => {
    const targetSymbol = sym ?? symbol;
    if (!targetSymbol) return;
    try {
      setLoading(true);
      const res = await api.get<Transaction[]>("/transactions", {
        params: { symbol: targetSymbol },
      });
      setTransactions(res.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch transactions");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  const createTransaction = useCallback(async (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => {
    const res = await api.post<Transaction>("/transactions", data);
    setTransactions((prev) => [...prev, res.data]);
    return res.data;
  }, []);

  const updateTransaction = useCallback(async (id: string, data: Partial<Transaction>) => {
    const res = await api.put<Transaction>(`/transactions/${id}`, data);
    setTransactions((prev) =>
      prev.map((t) => (t.id === id ? res.data : t))
    );
    return res.data;
  }, []);

  const deleteTransaction = useCallback(async (id: string) => {
    await api.delete(`/transactions/${id}`);
    setTransactions((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return {
    transactions,
    loading,
    error,
    fetchTransactions,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  };
}
