import { useState, useEffect, useCallback } from "react";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { useFundamentals } from "../hooks/useFundamentals";
import { AssetClassesTable } from "../components/AssetClassesTable";
import { HoldingsTable } from "../components/HoldingsTable";
import { DividendsTable } from "../components/DividendsTable";
import { PortfolioCompositionChart } from "../components/PortfolioCompositionChart";
import type { QuarantineStatus, Transaction } from "../types";
import api from "../services/api";

interface DividendAsset {
  symbol: string;
  annual_income: number;
  currency: string;
}

interface DividendClassData {
  assets: DividendAsset[];
}

interface DividendsResponse {
  dividends: DividendClassData[];
}

export default function Portfolio() {
  const { assetClasses, loading: classesLoading, createClass, updateClass, deleteClass } = useAssetClasses();
  const { holdings, allocation, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const {
    transactions,
    fetchTransactions,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  } = useTransactions();
  const { scores: fundamentalsScores, refreshAll: refreshAllScores, refresh: refreshScores } = useFundamentals();

  const [quarantineStatuses, setQuarantineStatuses] = useState<QuarantineStatus[]>([]);
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [dividendsBySymbol, setDividendsBySymbol] = useState<Map<string, { income: number; currency: string }>>(new Map());

  const fetchQuarantineStatuses = useCallback(async () => {
    try {
      const res = await api.get<QuarantineStatus[]>("/quarantine/status");
      setQuarantineStatuses(res.data);
    } catch {
      // silently fail
    }
  }, []);

  const fetchAllTransactions = useCallback(async () => {
    try {
      const res = await api.get<Transaction[]>("/transactions");
      setAllTransactions(res.data);
    } catch {
      // silently fail
    }
  }, []);

  const fetchDividends = useCallback(async () => {
    try {
      const res = await api.get<DividendsResponse>("/portfolio/dividends");
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
    fetchAllTransactions();
    fetchDividends();
  }, [fetchQuarantineStatuses, fetchAllTransactions, fetchDividends]);

  const allocationMap = allocation.reduce<Record<string, { actual_weight: number; diff: number }>>((acc, a) => {
    const cls = assetClasses.find((c) => c.id === a.asset_class_id);
    acc[a.asset_class_id] = {
      actual_weight: a.actual_weight,
      diff: a.actual_weight - (cls?.target_weight ?? a.target_weight),
    };
    return acc;
  }, {});

  const dividends = allTransactions.filter((t) => t.type === "dividend");

  const handleCreateTransaction = async (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => {
    await createTransaction(data);
    refreshPortfolio();
    fetchAllTransactions();
    fetchQuarantineStatuses();
  };

  const handleUpdateTransaction = async (id: string, data: Partial<Transaction>) => {
    await updateTransaction(id, data);
    refreshPortfolio();
    fetchAllTransactions();
  };

  const handleDeleteTransaction = async (id: string) => {
    await deleteTransaction(id);
    refreshPortfolio();
    fetchAllTransactions();
    fetchQuarantineStatuses();
  };

  const handleDeleteHolding = async (symbol: string) => {
    await api.delete(`/transactions/by-symbol/${symbol}`);
    refreshPortfolio();
    fetchAllTransactions();
    fetchQuarantineStatuses();
  };

  const handleChangeAssetClass = async (symbol: string, assetClassId: string) => {
    await api.put(`/transactions/by-symbol/${symbol}/asset-class`, null, {
      params: { asset_class_id: assetClassId },
    });
    refreshPortfolio();
    fetchAllTransactions();
  };

  const handleFetchTransactions = async (symbol: string) => {
    await fetchTransactions(symbol);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Portfolio</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <AssetClassesTable
            assetClasses={assetClasses}
            loading={classesLoading}
            allocationMap={allocationMap}
            onUpdateClass={async (id, data) => {
              await updateClass(id, data);
              refreshPortfolio();
            }}
            onCreateClass={async (name, weight) => {
              await createClass(name, weight);
            }}
            onDeleteClass={async (id) => {
              await deleteClass(id);
              refreshPortfolio();
            }}
          />
        </div>
        <div>
          <PortfolioCompositionChart
            allocation={allocation.map((a) => ({
              class_name: a.class_name,
              actual_weight: a.actual_weight,
              target_weight: a.target_weight,
            }))}
          />
        </div>
      </div>

      <HoldingsTable
        holdings={holdings}
        assetClasses={assetClasses}
        loading={portfolioLoading}
        quarantineStatuses={quarantineStatuses}
        transactions={transactions}
        dividendsBySymbol={dividendsBySymbol}
        fundamentalsScores={fundamentalsScores}
        showAddAsset
        onRefreshAllScores={async () => {
          await refreshAllScores();
          // Poll for results since scoring runs in background
          setTimeout(() => refreshScores(), 5000);
          setTimeout(() => refreshScores(), 15000);
          setTimeout(() => refreshScores(), 30000);
        }}
        onFetchTransactions={handleFetchTransactions}
        onCreateTransaction={handleCreateTransaction}
        onUpdateTransaction={handleUpdateTransaction}
        onDeleteTransaction={handleDeleteTransaction}
        onDeleteHolding={handleDeleteHolding}
        onChangeAssetClass={handleChangeAssetClass}
      />

      <DividendsTable
        dividends={dividends}
        loading={false}
        onCreateTransaction={handleCreateTransaction}
        defaultAssetClassId={assetClasses[0]?.id}
      />
    </div>
  );
}
