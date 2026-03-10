import { PerformanceChart } from "../components/PerformanceChart";
import { AllocationChart } from "../components/AllocationChart";
import { PortfolioCompositionChart } from "../components/PortfolioCompositionChart";
import { RecommendationCard } from "../components/RecommendationCard";
import { usePortfolio } from "../hooks/usePortfolio";
import { useRecommendations } from "../hooks/useRecommendations";

export default function Dashboard() {
  const { allocation, loading: portfolioLoading } = usePortfolio();
  const savedCount = localStorage.getItem("recommendationCount");
  const count = savedCount ? parseInt(savedCount, 10) : 2;
  const { recommendations, loading: recsLoading } = useRecommendations(count);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Top row: Performance chart full width */}
      <PerformanceChart />

      {/* Middle row: Allocation + Composition side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {portfolioLoading ? (
          <p className="text-gray-500 text-sm">Loading allocation...</p>
        ) : (
          <>
            <AllocationChart allocation={allocation} />
            <PortfolioCompositionChart allocation={allocation} />
          </>
        )}
      </div>

      {/* Bottom: Recommendations */}
      {recsLoading ? (
        <p className="text-gray-500 text-sm">Loading recommendations...</p>
      ) : (
        <RecommendationCard recommendations={recommendations} />
      )}
    </div>
  );
}
