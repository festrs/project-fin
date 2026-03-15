import type { Recommendation } from "../types";

interface RecommendationCardProps {
  recommendations: Recommendation[];
}

export function RecommendationCard({ recommendations }: RecommendationCardProps) {
  if (recommendations.length === 0) {
    return (
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <h3 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Recommendations</h3>
        <p className="text-text-muted text-base">No recommendations available</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <h3 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Recommendations</h3>
      <ul className="space-y-2">
        {recommendations.map((rec) => (
          <li
            key={rec.symbol}
            className="flex items-center justify-between p-3 rounded-lg even:bg-[var(--glass-row-alt)]"
          >
            <div>
              <span className="font-semibold text-text-primary">{rec.symbol}</span>
              <span className="text-text-muted text-base ml-2">{rec.class_name}</span>
            </div>
            <div className="flex items-center gap-1">
              {rec.diff > 0 ? (
                <span className="text-positive font-semibold text-base flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                  +{rec.diff.toFixed(1)}%
                </span>
              ) : (
                <span className="text-negative font-semibold text-base">
                  {rec.diff.toFixed(1)}%
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
