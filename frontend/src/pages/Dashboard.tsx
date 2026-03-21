import { useState, useEffect, useCallback } from "react";
import { computeClassSummaries } from "../components/ClassSummaryTable";
import BackgroundGradients from "../components/BackgroundGradients";
import PortfolioHeroCard from "../components/PortfolioHeroCard";
import AssetDistributionTable from "../components/AssetDistributionTable";
import AllocationDonutChart from "../components/AllocationDonutChart";
import BuyRecommendationCard from "../components/BuyRecommendationCard";
import NewsCard from "../components/NewsCard";
import CorporateEventAlert from "../components/CorporateEventAlert";
import { usePortfolio } from "../hooks/usePortfolio";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { useSplits } from "../hooks/useSplits";
import type { Transaction, AssetClass } from "../types";
import api from "../services/api";

interface DividendClassData {
  asset_class_id: string;
  class_name: string;
  annual_income: { amount: string; currency: string };
  currency: string;
}

interface DividendsResponse {
  dividends: DividendClassData[];
  total_annual_income: { amount: string; currency: string };
}

// Color mapping for donut chart segments
const CLASS_COLORS: Record<string, string> = {
  US: "#00e5ff",
  BR: "#22d3ee",
  crypto: "#a78bfa",
  fixed_income: "#34d399",
  emergency_reserve: "#fbbf24",
};

function getClassColor(ac: AssetClass): string {
  if (ac.is_emergency_reserve) return CLASS_COLORS.emergency_reserve;
  if (ac.type === "crypto") return CLASS_COLORS.crypto;
  if (ac.type === "fixed_income") return CLASS_COLORS.fixed_income;
  if (ac.country === "US") return CLASS_COLORS.US;
  return CLASS_COLORS.BR;
}

export default function Dashboard() {
  const { holdings, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const { assetClasses, loading: classesLoading, updateClass, createClass, deleteClass } = useAssetClasses();
  const { pendingSplits, actionLoading, applySplit, dismissSplit } = useSplits();

  const [manualDividends, setManualDividends] = useState<Transaction[]>([]);
  const [estimatedDividends, setEstimatedDividends] = useState<DividendsResponse | null>(null);
  const [usdToBrl, setUsdToBrl] = useState<number>(5.15);
  const [scrapingDividends, setScrapingDividends] = useState(false);

  const fetchManualDividends = useCallback(async () => {
    try {
      const res = await api.get<Transaction[]>("/transactions");
      setManualDividends(res.data.filter((t) => t.type === "dividend"));
    } catch { /* silently fail */ }
  }, []);

  const fetchEstimatedDividends = useCallback(async () => {
    try {
      const res = await api.get<DividendsResponse>("/portfolio/dividends");
      setEstimatedDividends(res.data);
    } catch { /* silently fail */ }
  }, []);

  const fetchExchangeRate = useCallback(async () => {
    try {
      const res = await api.get<{ pair: string; rate: number }>("/portfolio/exchange-rate?pair=USD-BRL");
      setUsdToBrl(res.data.rate);
    } catch { /* keep fallback */ }
  }, []);

  useEffect(() => {
    fetchManualDividends();
    fetchEstimatedDividends();
    fetchExchangeRate();
  }, [fetchManualDividends, fetchEstimatedDividends, fetchExchangeRate]);

  const loading = portfolioLoading || classesLoading;
  const { regular: regularSummaries, reserve: reserveSummary, grandTotalBRL } = computeClassSummaries(holdings, assetClasses, usdToBrl);

  const grandTotalWithReserve = grandTotalBRL + (reserveSummary?.totalValueBRL ?? 0);

  // Build donut chart data
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));
  const donutData = regularSummaries.map((s) => {
    const ac = classMap.get(s.classId);
    return {
      className: s.className,
      percentage: s.percentage,
      targetWeight: s.targetWeight,
      color: ac ? getClassColor(ac) : "#666",
    };
  });

  const handleScrapeDividends = useCallback(async () => {
    try {
      setScrapingDividends(true);
      await api.post("/dividends/scrape");
      const poll = setInterval(async () => {
        try {
          const res = await api.get<{ running: boolean }>("/dividends/scrape/status");
          if (!res.data.running) {
            clearInterval(poll);
            setScrapingDividends(false);
            fetchEstimatedDividends();
          }
        } catch { clearInterval(poll); setScrapingDividends(false); }
      }, 5000);
    } catch { setScrapingDividends(false); }
  }, [fetchEstimatedDividends]);

  const handleUpdateTargetWeight = async (classId: string, weight: number) => {
    await updateClass(classId, { target_weight: weight });
    refreshPortfolio();
  };

  return (
    <div className="relative">
      <BackgroundGradients />

      <div className="relative z-10 space-y-6">
        {/* Row 1: Portfolio Value Hero */}
        <PortfolioHeroCard grandTotalBRL={grandTotalWithReserve} loading={loading} />

        {/* Row 2: Asset Distribution Table */}
        <AssetDistributionTable
          holdings={holdings}
          assetClasses={assetClasses}
          manualDividends={manualDividends}
          estimatedDividends={estimatedDividends}
          loading={loading}
          usdToBrl={usdToBrl}
          onUpdateTargetWeight={handleUpdateTargetWeight}
          onScrapeDividends={handleScrapeDividends}
          scrapingDividends={scrapingDividends}
          onCreateClass={async (name, weight, type, isEmergencyReserve, country) => {
            await createClass(name, weight, type, isEmergencyReserve, country);
            refreshPortfolio();
          }}
          onDeleteClass={async (classId) => {
            await deleteClass(classId);
            refreshPortfolio();
          }}
        />

        {/* Row 3: Donut chart + Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AllocationDonutChart classSummaries={donutData} />
          <div className="grid grid-cols-1 gap-6">
            <BuyRecommendationCard />
            <NewsCard />
          </div>
        </div>

        {/* Row 4: Corporate Events */}
        <CorporateEventAlert
          splits={pendingSplits}
          actionLoading={actionLoading}
          onApply={applySplit}
          onDismiss={dismissSplit}
        />
      </div>
    </div>
  );
}
