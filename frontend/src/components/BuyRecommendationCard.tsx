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
    <div className="card">
      <div className="card-title">Top Buy Recommendation</div>
      {loading ? (
        <div className="animate-pulse" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ height: 16, width: 200, borderRadius: 4, background: "var(--surface-hover)" }} />
          <div style={{ height: 14, width: 300, borderRadius: 4, background: "var(--surface-hover)" }} />
        </div>
      ) : rec ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 10,
                background: "rgba(52, 199, 89, 0.15)",
                color: "var(--green)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {rec.symbol.slice(0, 4)}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>{rec.symbol}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                {rec.class_name} &middot; Under-allocated {Math.abs(rec.diff).toFixed(1)}%
              </div>
            </div>
            <Link to="/invest" className="btn-ghost" style={{ fontSize: 12, padding: "6px 14px" }}>
              View Analysis
            </Link>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Your {rec.class_name} is under-allocated by {Math.abs(rec.diff).toFixed(1)}%. Consider buying {rec.symbol}.
          </div>
        </>
      ) : (
        <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
          Portfolio is balanced. No buy recommendations.
        </p>
      )}
    </div>
  );
}
