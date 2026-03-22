import { useState, useEffect, useCallback } from "react";
import { computeClassSummaries } from "../components/ClassSummaryTable";
import PortfolioHeroCard from "../components/PortfolioHeroCard";
import AssetDistributionTable from "../components/AssetDistributionTable";
import AllocationDonutChart from "../components/AllocationDonutChart";
import BuyRecommendationCard from "../components/BuyRecommendationCard";
import NewsCard from "../components/NewsCard";
import CorporateEventAlert from "../components/CorporateEventAlert";
import { usePortfolio } from "../hooks/usePortfolio";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { useSplits } from "../hooks/useSplits";
import type { Transaction, AssetClass, DividendsResponse } from "../types";
import api from "../services/api";

// Wide-range pastel palette — each class gets a unique, highly distinct color
const CLASS_PALETTE = [
  "#6aadff", // soft blue
  "#d4a843", // muted gold
  "#e05c8a", // rose pink
  "#45b88c", // teal green
  "#a78bfa", // lavender
  "#f4845f", // salmon
  "#56c4e8", // sky cyan
  "#c7a24e", // amber
  "#7c6dd8", // indigo
  "#e8b84d", // warm yellow
];

function getClassColor(_ac: AssetClass, index: number): string {
  return CLASS_PALETTE[index % CLASS_PALETTE.length];
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
  const donutData = regularSummaries.map((s, index) => {
    const ac = classMap.get(s.classId);
    return {
      className: s.className,
      percentage: s.percentage,
      targetWeight: s.targetWeight,
      color: ac ? getClassColor(ac, index) : "#666",
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
    <div>
      <div className="space-y-6">
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
