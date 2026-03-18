import { useState, useEffect, useCallback } from "react";
import { PerformanceChart } from "../components/PerformanceChart";
import { AllocationChart } from "../components/AllocationChart";
import { PortfolioCompositionChart } from "../components/PortfolioCompositionChart";
import { ClassSummaryTable, computeClassSummaries } from "../components/ClassSummaryTable";
import { RecommendationCard } from "../components/RecommendationCard";
import { usePortfolio } from "../hooks/usePortfolio";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { useRecommendations } from "../hooks/useRecommendations";
import { useSplits } from "../hooks/useSplits";
import type { Transaction } from "../types";
import api from "../services/api";

interface DividendClassData {
  asset_class_id: string;
  class_name: string;
  annual_income: number;
  currency: string;
}

interface DividendsResponse {
  dividends: DividendClassData[];
  total_annual_income: number;
}

export default function Dashboard() {
  const { holdings, allocation, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const { assetClasses, loading: classesLoading, updateClass } = useAssetClasses();
  const savedCount = localStorage.getItem("recommendationCount");
  const count = savedCount ? parseInt(savedCount, 10) : 2;
  const { recommendations, loading: recsLoading } = useRecommendations(count);
  const { pendingSplits, applySplit, dismissSplit } = useSplits();

  const [manualDividends, setManualDividends] = useState<Transaction[]>([]);
  const [estimatedDividends, setEstimatedDividends] = useState<DividendsResponse | null>(null);
  const [usdToBrl, setUsdToBrl] = useState<number>(5.15);

  const fetchManualDividends = useCallback(async () => {
    try {
      const res = await api.get<Transaction[]>("/transactions");
      setManualDividends(res.data.filter((t) => t.type === "dividend"));
    } catch {
      // silently fail
    }
  }, []);

  const fetchEstimatedDividends = useCallback(async () => {
    try {
      const res = await api.get<DividendsResponse>("/portfolio/dividends");
      setEstimatedDividends(res.data);
    } catch {
      // silently fail
    }
  }, []);

  const fetchExchangeRate = useCallback(async () => {
    try {
      const res = await api.get<{ pair: string; rate: number }>("/portfolio/exchange-rate?pair=USD-BRL");
      setUsdToBrl(res.data.rate);
    } catch {
      // keep fallback
    }
  }, []);

  useEffect(() => {
    fetchManualDividends();
    fetchEstimatedDividends();
    fetchExchangeRate();
  }, [fetchManualDividends, fetchEstimatedDividends, fetchExchangeRate]);

  const loading = portfolioLoading || classesLoading;
  const classSummaries = !loading
    ? computeClassSummaries(holdings, assetClasses, usdToBrl).map((s) => ({
        className: s.className,
        percentage: s.percentage,
        targetWeight: s.targetWeight,
      }))
    : [];

  const handleUpdateTargetWeight = async (classId: string, weight: number) => {
    await updateClass(classId, { target_weight: weight });
    refreshPortfolio();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Dashboard</h1>

      {pendingSplits.length > 0 && (
        <div className="space-y-2">
          {pendingSplits.map((split) => (
            <div key={split.id} className="glass-card p-4 border border-yellow-500/30 bg-yellow-500/5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-text-primary font-medium">
                    Stock split detected: {split.symbol} ({split.from_factor}:{split.to_factor} on{" "}
                    {new Date(split.split_date).toLocaleDateString()})
                  </p>
                  <p className="text-text-muted text-sm mt-1">
                    Your {split.current_quantity} shares will become {split.new_quantity} shares.
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => applySplit(split.id)}
                    className="px-3 py-1.5 text-sm rounded-lg bg-accent/20 text-accent hover:bg-accent/30 transition-colors"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => dismissSplit(split.id)}
                    className="px-3 py-1.5 text-sm rounded-lg bg-surface-card text-text-muted hover:text-text-primary transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Top row: Summary table + Donut chart side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ClassSummaryTable
            holdings={holdings}
            assetClasses={assetClasses}
            manualDividends={manualDividends}
            estimatedDividends={estimatedDividends}
            loading={loading}
            usdToBrl={usdToBrl}
            onUpdateTargetWeight={handleUpdateTargetWeight}
          />
        </div>
        <div>
          <PortfolioCompositionChart classSummaries={classSummaries} />
        </div>
      </div>

      {/* Performance chart */}
      <PerformanceChart />

      {/* Allocation bar chart */}
      {!portfolioLoading && (
        <AllocationChart allocation={allocation} />
      )}

      {/* Recommendations */}
      {recsLoading ? (
        <p className="text-text-muted text-base">Loading recommendations...</p>
      ) : (
        <RecommendationCard recommendations={recommendations} />
      )}
    </div>
  );
}
