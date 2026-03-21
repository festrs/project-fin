import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

interface Recommendation {
  symbol: string;
  class_name: string;
  diff: number;
}

export default function BuyRecommendationCard() {
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ recommendations: Recommendation[] }>("/recommendations", { params: { count: 1 } })
      .then((res) => {
        if (res.data.recommendations.length > 0) {
          setRec(res.data.recommendations[0]);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card flex flex-col justify-between h-full">
      <div>
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-primary mb-4"
          style={{ background: "var(--glass-primary-soft)" }}
        >
          <span className="material-symbols-outlined">account_balance_wallet</span>
        </div>
        <h5 className="text-sm font-bold text-on-surface mb-1 font-body">
          Buy Order Recommendation
        </h5>
        {loading ? (
          <div className="h-4 w-48 rounded animate-pulse" style={{ background: "var(--color-surface-high)" }} />
        ) : rec ? (
          <p className="text-xs text-on-surface-variant font-body">
            Your <span className="text-primary font-medium">{rec.class_name}</span> is under-allocated by{" "}
            <span className="text-secondary font-medium">{Math.abs(rec.diff).toFixed(1)}%</span>.
            Consider buying <span className="text-on-surface font-medium">{rec.symbol}</span>.
          </p>
        ) : (
          <p className="text-xs text-on-surface-variant font-body">
            Portfolio is balanced. No buy recommendations.
          </p>
        )}
      </div>
      <Link
        to="/invest"
        className="mt-4 text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1 self-start font-body"
      >
        View Details <span className="material-symbols-outlined text-sm">chevron_right</span>
      </Link>
    </div>
  );
}
