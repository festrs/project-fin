import { useState, useEffect, useCallback } from "react";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { AssetClassesTable } from "../components/AssetClassesTable";
import { HoldingsTable } from "../components/HoldingsTable";
import { DividendsTable } from "../components/DividendsTable";
import { PortfolioCompositionChart } from "../components/PortfolioCompositionChart";
import type { QuarantineStatus, Transaction } from "../types";
import api from "../services/api";

export default function Portfolio() {
  const { assetClasses, loading: classesLoading, createClass, updateClass, deleteClass } = useAssetClasses();
  const { holdings, allocation, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const {
    transactions,
    fetchTransactions,
    createTransaction,
  } = useTransactions();

  const [quarantineStatuses, setQuarantineStatuses] = useState<QuarantineStatus[]>([]);
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);

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

  useEffect(() => {
    fetchQuarantineStatuses();
    fetchAllTransactions();
  }, [fetchQuarantineStatuses, fetchAllTransactions]);

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

  const handleFetchTransactions = async (symbol: string) => {
    await fetchTransactions(symbol);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Portfolio</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
        onFetchTransactions={handleFetchTransactions}
        onCreateTransaction={handleCreateTransaction}
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
