import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { useFundamentals } from "../hooks/useFundamentals";
import { HoldingsTable } from "../components/HoldingsTable";
import { AddAssetForm } from "../components/AddAssetForm";
import { moneyToNumber } from "../utils/money";
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
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({});
  const [fundamentalsLoading, setFundamentalsLoading] = useState<string | null>(null);

  const assetClass = assetClasses.find((ac) => ac.id === assetClassId);
  const classHoldings = holdings.filter((h) => h.asset_class_id === assetClassId);
  const type = assetClass?.type ?? "stock";
  const isReserve = assetClass?.is_emergency_reserve ?? false;

  const toBRL = (value: number, cur: string) => {
    if (cur === "BRL") return value;
    const rate = exchangeRates[`${cur}-BRL`];
    return rate ? value * rate : value;
  };

  const totalValueBRL = classHoldings.reduce((sum, h) => {
    const value = moneyToNumber(h.current_value ?? h.total_cost);
    const cur = h.total_cost.currency;
    return sum + toBRL(value, cur);
  }, 0);

  const fetchExchangeRates = useCallback(async () => {
    const pairs = ["USD-BRL", "EUR-BRL"];
    const rates: Record<string, number> = {};
    await Promise.all(
      pairs.map(async (pair) => {
        try {
          const res = await api.get<{ rate: number }>("/portfolio/exchange-rate", {
            params: { pair },
          });
          rates[pair] = res.data.rate;
        } catch {
          // silently fail
        }
      })
    );
    setExchangeRates(rates);
  }, []);

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
      const res = await api.get<{ dividends: Array<{ assets: Array<{ symbol: string; annual_income: { amount: string; currency: string }; currency: string }> }> }>("/portfolio/dividends");
      const map = new Map<string, { income: number; currency: string }>();
      for (const cls of res.data.dividends) {
        for (const asset of cls.assets) {
          map.set(asset.symbol, { income: parseFloat(asset.annual_income.amount), currency: asset.currency });
        }
      }
      setDividendsBySymbol(map);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    fetchExchangeRates();
    fetchQuarantineStatuses();
    fetchDividends();
  }, [fetchExchangeRates, fetchQuarantineStatuses, fetchDividends]);

  const handleCreateTransaction = async (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => {
    const result = await createTransaction(data);
    refreshPortfolio();
    fetchQuarantineStatuses();

    // Poll for fundamentals if a background refresh was started
    if (result && 'fundamentals_refresh_started' in result && result.fundamentals_refresh_started) {
      const symbol = data.asset_symbol;
      setFundamentalsLoading(symbol);
      const poll = async (attempts: number) => {
        if (attempts <= 0) {
          setFundamentalsLoading(null);
          return;
        }
        await new Promise((r) => setTimeout(r, 5000));
        try {
          await api.get(`/fundamentals/${symbol}`);
          // Score exists now
          setFundamentalsLoading(null);
          refreshScores();
        } catch {
          // Not ready yet, keep polling
          poll(attempts - 1);
        }
      };
      poll(6); // Poll up to 6 times (30s total)
    }
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

  if (!assetClass) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-primary hover:text-primary-hover text-base">
          &lsaquo; Dashboard
        </Link>
        <p className="text-text-muted">Asset class not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-primary hover:text-primary-hover text-base">
          &lsaquo; Dashboard
        </Link>
        <span className="text-text-muted">/</span>
        <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">
          {assetClass.name}
        </h1>
        <span className="ml-auto text-text-muted text-base">
          Total: R${totalValueBRL.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          {isReserve && <span className="ml-2 text-xs bg-[var(--glass-primary-soft)] px-2 py-0.5 rounded">(Emergency Reserve)</span>}
        </span>
      </div>

      <AddAssetForm
        type={type}
        assetClassId={assetClassId!}
        onSubmit={handleCreateTransaction}
        onCancel={() => {/* no-op: form is always visible */}}
      />

      {fundamentalsLoading && (
        <div className="flex items-center gap-2 px-4 py-3 bg-[var(--glass-primary-soft)] border border-[var(--glass-border)] rounded-[10px] text-base text-primary">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>Fetching fundamentals for <strong>{fundamentalsLoading}</strong>...</span>
        </div>
      )}

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
        exchangeRates={exchangeRates}
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
