import type { Recommendation } from "../types";

interface RecommendationCardProps {
  recommendations: Recommendation[];
}

export function RecommendationCard({ recommendations }: RecommendationCardProps) {
  if (recommendations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-3">Recommendations</h3>
        <p className="text-gray-500 text-sm">No recommendations available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-3">Recommendations</h3>
      <ul className="space-y-2">
        {recommendations.map((rec) => (
          <li
            key={rec.symbol}
            className="flex items-center justify-between p-2 rounded border border-gray-100"
          >
            <div>
              <span className="font-medium">{rec.symbol}</span>
              <span className="text-gray-500 text-sm ml-2">{rec.class_name}</span>
            </div>
            <div className="flex items-center gap-1">
              {rec.diff > 0 ? (
                <span className="text-green-600 font-medium flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 15l7-7 7 7"
                    />
                  </svg>
                  +{rec.diff.toFixed(1)}%
                </span>
              ) : (
                <span className="text-red-600 font-medium">
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
