import { useState, useEffect, useCallback } from "react";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { AssetClassesTable } from "../components/AssetClassesTable";
import { DividendsTable } from "../components/DividendsTable";
import { PortfolioCompositionChart } from "../components/PortfolioCompositionChart";
import type { Transaction } from "../types";
import api from "../services/api";

export default function Portfolio() {
  const { assetClasses, loading: classesLoading, createClass, updateClass, deleteClass } = useAssetClasses();
  const { allocation, refresh: refreshPortfolio } = usePortfolio();
  const { createTransaction } = useTransactions();

  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);

  const fetchAllTransactions = useCallback(async () => {
    try {
      const res = await api.get<Transaction[]>("/transactions");
      setAllTransactions(res.data);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    fetchAllTransactions();
  }, [fetchAllTransactions]);

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
            onCreateClass={async (name, weight, type) => {
              await createClass(name, weight, type);
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

      <DividendsTable
        dividends={dividends}
        loading={false}
        onCreateTransaction={handleCreateTransaction}
        defaultAssetClassId={assetClasses[0]?.id}
      />
    </div>
  );
}
