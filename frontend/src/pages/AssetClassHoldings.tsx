import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { useFundamentals } from "../hooks/useFundamentals";
import { HoldingsTable } from "../components/HoldingsTable";
import { AddAssetForm } from "../components/AddAssetForm";
import type { QuarantineStatus, Transaction } from "../types";
import api from "../services/api";

export default function AssetClassHoldings() {
  const { assetClassId } = useParams<{ assetClassId: string }>();
  const { assetClasses } = useAssetClasses();
  const { holdings, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const {
    transactions,
    fetchTransactions,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  } = useTransactions();
  const { scores: fundamentalsScores, refreshAll: refreshAllScores, refresh: refreshScores } = useFundamentals();

  const [quarantineStatuses, setQuarantineStatuses] = useState<QuarantineStatus[]>([]);
  const [dividendsBySymbol, setDividendsBySymbol] = useState<Map<string, { income: number; currency: string }>>(new Map());

  const assetClass = assetClasses.find((ac) => ac.id === assetClassId);
  const classHoldings = holdings.filter((h) => h.asset_class_id === assetClassId);
  const type = assetClass?.type ?? "stock";

  const totalValue = classHoldings.reduce(
    (sum, h) => sum + (h.current_value ?? h.total_cost),
    0
  );
  const currency = classHoldings[0]?.currency ?? "USD";

  const fetchQuarantineStatuses = useCallback(async () => {
    try {
      const res = await api.get<QuarantineStatus[]>("/quarantine/status");
      setQuarantineStatuses(res.data);
    } catch {
      // silently fail
    }
  }, []);

  const fetchDividends = useCallback(async () => {
    try {
      const res = await api.get<{ dividends: Array<{ assets: Array<{ symbol: string; annual_income: number; currency: string }> }> }>("/portfolio/dividends");
      const map = new Map<string, { income: number; currency: string }>();
      for (const cls of res.data.dividends) {
        for (const asset of cls.assets) {
          map.set(asset.symbol, { income: asset.annual_income, currency: asset.currency });
        }
      }
      setDividendsBySymbol(map);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    fetchQuarantineStatuses();
    fetchDividends();
  }, [fetchQuarantineStatuses, fetchDividends]);

  const handleCreateTransaction = async (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => {
    await createTransaction(data);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleUpdateTransaction = async (id: string, data: Partial<Transaction>) => {
    await updateTransaction(id, data);
    refreshPortfolio();
  };

  const handleDeleteTransaction = async (id: string) => {
    await deleteTransaction(id);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleDeleteHolding = async (symbol: string) => {
    await api.delete(`/transactions/by-symbol/${symbol}`);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleChangeAssetClass = async (symbol: string, newAssetClassId: string) => {
    await api.put(`/transactions/by-symbol/${symbol}/asset-class`, null, {
      params: { asset_class_id: newAssetClassId },
    });
    refreshPortfolio();
  };

  const CURRENCY_SYMBOLS: Record<string, string> = {
    BRL: "R$",
    USD: "$",
    EUR: "\u20AC",
    GBP: "\u00A3",
  };
  const currencySymbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;

  if (!assetClass) {
    return (
      <div className="space-y-4">
        <Link to="/portfolio" className="text-primary hover:text-primary-hover text-base">
          &lsaquo; Portfolio
        </Link>
        <p className="text-text-muted">Asset class not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/portfolio" className="text-primary hover:text-primary-hover text-base">
          &lsaquo; Portfolio
        </Link>
        <span className="text-text-muted">/</span>
        <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">
          {assetClass.name}
        </h1>
        <span className="ml-auto text-text-muted text-base">
          Total: {currencySymbol}{totalValue.toFixed(2)}
        </span>
      </div>

      <AddAssetForm
        type={type}
        assetClassId={assetClassId!}
        onSubmit={handleCreateTransaction}
        onCancel={() => {/* no-op: form is always visible */}}
      />

      <HoldingsTable
        holdings={classHoldings}
        assetClassId={assetClassId!}
        assetClasses={assetClasses}
        type={type}
        loading={portfolioLoading}
        quarantineStatuses={quarantineStatuses}
        transactions={transactions}
        dividendsBySymbol={dividendsBySymbol}
        fundamentalsScores={fundamentalsScores}
        onRefreshAllScores={async () => {
          await refreshAllScores();
          setTimeout(() => refreshScores(), 5000);
          setTimeout(() => refreshScores(), 15000);
          setTimeout(() => refreshScores(), 30000);
        }}
        onFetchTransactions={fetchTransactions}
        onCreateTransaction={handleCreateTransaction}
        onUpdateTransaction={handleUpdateTransaction}
        onDeleteTransaction={handleDeleteTransaction}
        onDeleteHolding={handleDeleteHolding}
        onChangeAssetClass={handleChangeAssetClass}
      />
    </div>
  );
}
